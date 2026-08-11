import asyncio
import logging
import os
import platform
import random
import sys
import webbrowser
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import httpx
from packaging.version import Version
from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from app.services import riot_auth
from callback import LocalCallback
from cloud_client import CloudClient
from config import settings
from credentials import CredentialStore
from local_riot import LocalRiotClient, RiotConnectionExpired
from local_store import LocalStore
from logging_setup import configure_logging
from pairing import PairingClient
from paths import LOG_DIR
from preferences import Preferences
from scheduler import backoff_seconds
from startup import set_startup
from version import __version__

logger = logging.getLogger(__name__)

STYLE = """
QWidget {
    background: #111311;
    color: #f1f2ed;
    font-family: "Segoe UI";
    font-size: 13px;
}
QMainWindow, QDialog { background: #111311; }
QLabel#Brand { color: #ff6572; font-size: 13px; font-weight: 800; letter-spacing: 2px; }
QLabel#Title { font-size: 26px; font-weight: 700; }
QLabel#Subtitle, QLabel#Muted { color: #959b92; }
QLabel#StatusText { font-size: 18px; font-weight: 700; }
QLabel#StatusDot {
    min-width: 10px; max-width: 10px; min-height: 10px; max-height: 10px;
    border-radius: 5px; background: #858b82;
}
QLabel#StatusDot[state="connected"] { background: #64d696; }
QLabel#StatusDot[state="reconnect"] { background: #ff6572; }
QLabel#StatusDot[state="offline"] { background: #e8b15c; }
QLabel#CloudPill {
    color: #aeb3ab; background: #222521; border: 1px solid #343934;
    border-radius: 12px; padding: 4px 10px; font-size: 11px; font-weight: 600;
}
QFrame#Panel { background: #191c19; border: 1px solid #303530; border-radius: 12px; }
QFrame#Divider { background: #303530; min-height: 1px; max-height: 1px; }
QLabel#MetricLabel { color: #858b82; font-size: 11px; font-weight: 600; }
QLabel#MetricValue { color: #f1f2ed; font-size: 14px; font-weight: 600; }
QPushButton {
    min-height: 40px; border: 1px solid #414741; border-radius: 8px;
    padding: 0 16px; background: #191c19; font-weight: 650;
}
QPushButton:hover { background: #252925; border-color: #606760; }
QPushButton:pressed { background: #303530; }
QPushButton:disabled { color: #686e67; border-color: #303530; }
QPushButton#Primary { background: #ff6572; color: white; border: 0; }
QPushButton#Primary:hover { background: #ff7a85; }
QPushButton#Quiet { background: transparent; border: 0; color: #aeb3ab; text-align: left; }
QPushButton#Quiet:hover { color: #f1f2ed; background: #222521; }
QPushButton#Danger { color: #ff7a85; }
QCheckBox { min-height: 34px; spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; }
"""


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class Worker(QRunnable):
    def __init__(self, function: Callable) -> None:
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            value = self.function()
            if asyncio.iscoroutine(value):
                value = asyncio.run(value)
            self.signals.result.emit(value)
        except Exception as exc:
            logger.exception("Background operation failed")
            self.signals.error.emit(user_error(exc))
        finally:
            self.signals.finished.emit()


def user_error(exc: Exception) -> str:
    if isinstance(exc, RiotConnectionExpired):
        return "Reconnect Riot to continue checking your shop."
    if isinstance(exc, httpx.RequestError):
        return "No internet connection. VALSHOP will retry automatically."
    text = str(exc)
    if not text or "token" in text.lower():
        return "VALSHOP could not complete that action. Please try again."
    return text


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("Divider")
    return line


class SettingsDialog(QDialog):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self.window = window
        self.setWindowTitle("VALSHOP Companion Settings")
        self.setModal(True)
        self.setFixedWidth(470)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Companion settings")
        title.setObjectName("Title")
        layout.addWidget(title)
        subtitle = QLabel("Background behavior for this Windows device.")
        subtitle.setObjectName("Muted")
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        self.startup_check = QCheckBox("Start VALSHOP Companion with Windows")
        self.startup_check.setChecked(bool(window.prefs.get("start_with_windows")))
        self.startup_check.toggled.connect(window.toggle_startup)
        layout.addWidget(self.startup_check)

        minimized = QCheckBox("Launch minimized to the system tray")
        minimized.setChecked(bool(window.prefs.get("launch_minimized")))
        minimized.toggled.connect(lambda value: window.prefs.set("launch_minimized", value))
        layout.addWidget(minimized)

        notifications = QCheckBox("Windows wishlist notifications")
        notifications.setChecked(bool(window.prefs.get("notifications_enabled")))
        notifications.toggled.connect(
            lambda value: window.prefs.set("notifications_enabled", value)
        )
        layout.addWidget(notifications)
        layout.addWidget(divider())

        open_logs = QPushButton("Open logs folder")
        open_logs.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_DIR)))
        )
        test_notification = QPushButton("Test Windows notification")
        test_notification.clicked.connect(window.test_notification)
        check_updates = QPushButton("Check for updates")
        check_updates.clicked.connect(window.check_updates)
        for button in (open_logs, test_notification, check_updates):
            layout.addWidget(button)

        layout.addWidget(divider())
        disconnect_device = QPushButton("Disconnect this device from VALSHOP Cloud")
        disconnect_device.setObjectName("Danger")
        disconnect_device.clicked.connect(window.disconnect_cloud)
        layout.addWidget(disconnect_device)

        forget_riot = QPushButton("Disconnect Riot on this PC")
        forget_riot.setObjectName("Danger")
        forget_riot.clicked.connect(window.disconnect_riot)
        layout.addWidget(forget_riot)

        about = QLabel(
            f"VALSHOP Companion {__version__}\n"
            "Independent and not affiliated with Riot Games.\n"
            "Riot credentials are entered only on Riot's website."
        )
        about.setObjectName("Muted")
        about.setWordWrap(True)
        layout.addWidget(about)

        close = QPushButton("Done")
        close.setObjectName("Primary")
        close.clicked.connect(self.accept)
        layout.addWidget(close)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        configure_logging()
        self.prefs = Preferences()
        self.credentials = CredentialStore()
        self.store = LocalStore()
        self.riot = LocalRiotClient(self.credentials)
        self.pool = QThreadPool.globalInstance()
        self.syncing = False
        self.retry_attempt = 0
        self.shop = self.store.get_cache("shop", {}) or {}
        self.next_sync_at: datetime | None = None
        self._quitting = False

        self.setWindowTitle(f"VALSHOP Companion {__version__}")
        self.setFixedSize(560, 625)
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "valshop.ico")
        self.icon = QIcon(icon_path)
        self.setWindowIcon(self.icon)

        self._build_ui()
        self._build_tray()
        self._restore_state()

        self.sync_timer = QTimer(self)
        self.sync_timer.setSingleShot(True)
        self.sync_timer.timeout.connect(self.sync_now)
        self.wake_timer = QTimer(self)
        self.wake_timer.setInterval(60_000)
        self.wake_timer.timeout.connect(self._check_overdue_sync)
        self.wake_timer.start()
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1_000)
        self.clock_timer.timeout.connect(self._update_next_check)
        self.clock_timer.start()
        QTimer.singleShot(500, self._startup)

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(16)

        brand_row = QHBoxLayout()
        brand = QLabel("VALSHOP")
        brand.setObjectName("Brand")
        brand_row.addWidget(brand)
        brand_row.addStretch()
        self.cloud_pill = QLabel("Cloud not paired")
        self.cloud_pill.setObjectName("CloudPill")
        brand_row.addWidget(self.cloud_pill)
        layout.addLayout(brand_row)

        title = QLabel("Companion")
        title.setObjectName("Title")
        layout.addWidget(title)
        subtitle = QLabel("Shop checks and notifications, quietly in the background.")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(subtitle)

        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 18, 20, 18)
        panel_layout.setSpacing(14)

        status_row = QHBoxLayout()
        self.status_dot = QLabel()
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setProperty("state", "reconnect")
        status_row.addWidget(self.status_dot)
        self.status_label = QLabel("Reconnect Riot")
        self.status_label.setObjectName("StatusText")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        panel_layout.addLayout(status_row)

        self.detail_label = QLabel("Connect Riot to begin automatic shop checks.")
        self.detail_label.setObjectName("Muted")
        self.detail_label.setWordWrap(True)
        panel_layout.addWidget(self.detail_label)
        panel_layout.addWidget(divider())

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(26)
        metrics.setVerticalSpacing(10)
        self.account_value = self._metric(metrics, 0, "ACCOUNT", "Not connected")
        self.last_sync_value = self._metric(metrics, 1, "LAST SHOP SYNC", "Never")
        self.next_check_value = self._metric(metrics, 2, "NEXT CHECK", "Waiting")
        panel_layout.addLayout(metrics)
        layout.addWidget(panel)

        self.open_button = QPushButton("Open VALSHOP Website")
        self.open_button.setObjectName("Primary")
        self.open_button.clicked.connect(self.open_website)
        layout.addWidget(self.open_button)

        actions = QGridLayout()
        actions.setSpacing(10)
        self.sync_button = QPushButton("Sync Now")
        self.sync_button.clicked.connect(self.sync_now)
        self.connect_button = QPushButton("Connect Riot")
        self.connect_button.clicked.connect(self.connect_riot)
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.show_settings)
        self.pair_button = QPushButton("Pair with Website")
        self.pair_button.clicked.connect(self.pair_cloud)
        actions.addWidget(self.sync_button, 0, 0)
        actions.addWidget(self.connect_button, 0, 1)
        actions.addWidget(settings_button, 1, 0)
        actions.addWidget(self.pair_button, 1, 1)
        layout.addLayout(actions)

        self.activity_label = QLabel("Ready")
        self.activity_label.setObjectName("Muted")
        self.activity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.activity_label.setWordWrap(True)
        layout.addWidget(self.activity_label)
        layout.addStretch()
        self.setCentralWidget(root)

    def _metric(self, layout: QGridLayout, row: int, label: str, value: str) -> QLabel:
        name = QLabel(label)
        name.setObjectName("MetricLabel")
        result = QLabel(value)
        result.setObjectName("MetricValue")
        result.setWordWrap(True)
        layout.addWidget(name, row, 0)
        layout.addWidget(result, row, 1)
        return result

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.icon, self)
        menu = QMenu("VALSHOP Companion")
        self.tray_status = QAction("Reconnect Riot", menu)
        self.tray_status.setEnabled(False)
        menu.addAction(self.tray_status)
        menu.addSeparator()

        for text, handler in (
            ("Open VALSHOP Website", self.open_website),
            ("Open Companion", self.show_main),
            ("Sync Now", self.sync_now),
        ):
            action = QAction(text, menu)
            action.triggered.connect(handler)
            menu.addAction(action)

        self.tray_reconnect = QAction("Reconnect Riot", menu)
        self.tray_reconnect.triggered.connect(self.connect_riot)
        menu.addAction(self.tray_reconnect)
        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)
        menu.addSeparator()
        quit_action = QAction("Quit VALSHOP Companion", menu)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.messageClicked.connect(self.open_website)
        self.tray.show()

    def _restore_state(self) -> None:
        self._update_account()
        self._update_cloud_state()
        if self.shop.get("fetched_at"):
            self.last_sync_value.setText(self._format_timestamp(self.shop["fetched_at"]))
        if self.riot.session:
            self._set_connection("Connected", "Restoring your secure Riot session.")
        else:
            self._set_connection("Reconnect Riot", "Connect Riot to begin automatic checks.")

    def _startup(self) -> None:
        def validated(valid: bool) -> None:
            if valid:
                self._set_connection("Connected", "Riot is connected. Checking your shop.")
                self.sync_now()
            else:
                self._set_connection(
                    "Reconnect Riot", "Your Riot session needs to be connected again."
                )
                self._report_reauth_required()

        self.run_worker(self.riot.validate, validated)
        if (
            not self.prefs.get("onboarding_complete")
            and os.environ.get("VALSHOP_SMOKE_TEST") != "1"
        ):
            self.show_onboarding()
        elif self.prefs.get("launch_minimized"):
            self.hide()

    def run_worker(
        self,
        function: Callable,
        on_result: Callable | None = None,
        on_error: Callable | None = None,
        on_finished: Callable | None = None,
    ) -> None:
        worker = Worker(function)
        if on_result:
            worker.signals.result.connect(on_result)
        worker.signals.error.connect(on_error or self.show_error)
        if on_finished:
            worker.signals.finished.connect(on_finished)
        self.pool.start(worker)

    def open_website(self) -> None:
        url = QUrl(settings.PUBLIC_SITE_URL)
        if url.scheme() not in {"http", "https"} or not url.host():
            self.show_error("The VALSHOP website URL is not configured for this build.")
            return
        QDesktopServices.openUrl(url)

    def show_main(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def show_settings(self) -> None:
        self.show_main()
        SettingsDialog(self).exec()

    def connect_riot(self) -> None:
        self.connect_button.setEnabled(False)
        self.connect_button.setText("Waiting for Riot...")
        self.activity_label.setText("Finish signing in through Riot in your browser.")

        def flow() -> dict:
            callback = LocalCallback()
            callback.start()
            webbrowser.open(riot_auth.get_auth_url())
            url = callback.wait()
            return asyncio.run(self.riot.connect(url))

        self.run_worker(
            flow,
            lambda _result: self._connected(),
            on_error=self._connect_failed,
            on_finished=lambda: self.connect_button.setEnabled(True),
        )

    def _connect_failed(self, message: str) -> None:
        self.connect_button.setText("Reconnect Riot" if self.riot.session else "Connect Riot")
        self.activity_label.setText(message)
        self.show_error(message)

    def _connected(self) -> None:
        self.connect_button.setText("Reconnect Riot")
        self._update_account()
        self._set_connection("Connected", "Riot connected securely. Refreshing your shop.")
        self.sync_now()

    def disconnect_riot(self) -> None:
        if QMessageBox.question(
            self,
            "Disconnect Riot",
            "Remove the locally stored Riot session from this PC?",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.riot.disconnect()
        self._update_account()
        self._set_connection("Reconnect Riot", "Riot is disconnected on this PC.")
        self.connect_button.setText("Connect Riot")
        self._report_reauth_required()

    def pair_cloud(self) -> None:
        if self.credentials.device_token():
            self.activity_label.setText("This companion is already paired with VALSHOP Cloud.")
            return
        self.pair_button.setEnabled(False)
        self.pair_button.setText("Waiting for approval...")
        self.activity_label.setText("Approve this device on the VALSHOP website.")
        client = PairingClient(settings.API_BASE_URL, settings.PUBLIC_SITE_URL, self.credentials)

        def paired(_token: str) -> None:
            self._update_cloud_state()
            self.activity_label.setText("Website pairing complete.")
            self.sync_now()

        def finished() -> None:
            self.pair_button.setEnabled(True)
            self._update_cloud_state()

        self.run_worker(
            lambda: client.pair(platform.node() or "Windows PC"),
            paired,
            on_finished=finished,
        )

    def disconnect_cloud(self) -> None:
        token = self.credentials.device_token()
        if not token:
            QMessageBox.information(self, "VALSHOP", "This device is not cloud-paired.")
            return
        if QMessageBox.question(
            self,
            "Disconnect this device",
            "Remove this PC from your VALSHOP account? Other PCs are not affected.",
        ) != QMessageBox.StandardButton.Yes:
            return

        async def flow() -> None:
            await CloudClient(settings.API_BASE_URL, token).revoke()

        def complete(_value: object = None) -> None:
            self.credentials.clear_device_token()
            self._update_cloud_state()
            self.activity_label.setText("This device was disconnected from VALSHOP Cloud.")

        self.run_worker(flow, complete)

    def sync_now(self) -> None:
        if self.syncing:
            return
        self.syncing = True
        self.sync_button.setEnabled(False)
        self.activity_label.setText("Refreshing your shop...")

        async def flow() -> dict:
            shop = await self.riot.fetch_shop()
            self.store.save_shop(shop)
            token = self.credentials.device_token()
            if token:
                try:
                    cloud = CloudClient(settings.API_BASE_URL, token)
                    for pending in self.store.pending():
                        payload = {
                            "rotation_key": pending["rotation_key"],
                            "seconds_remaining": pending["seconds_remaining"],
                            "offers": [
                                {
                                    "skin_uuid": offer["uuid"],
                                    "skin_name": offer["name"],
                                    "display_icon": offer.get("display_icon", ""),
                                    "content_tier_name": offer.get(
                                        "content_tier_name", "Unknown"
                                    ),
                                    "content_tier_color": offer.get(
                                        "content_tier_color", ""
                                    ),
                                    "vp_cost": offer["cost"],
                                }
                                for offer in pending["offers"]
                            ],
                        }
                        await cloud.sync(payload)
                        self.store.mark_uploaded(pending["rotation_key"])
                    self.store.set_wishlist(await cloud.wishlist())
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code in {401, 403}:
                        self.credentials.clear_device_token()
                        shop["cloud_pairing_lost"] = True
                    else:
                        shop["cloud_sync_pending"] = True
                except httpx.HTTPError as exc:
                    logger.warning(
                        "Cloud sync unavailable; normalized shop remains queued: %s",
                        type(exc).__name__,
                    )
                    shop["cloud_sync_pending"] = True
            return shop

        self.run_worker(
            flow,
            self._sync_success,
            self._sync_error,
            self._sync_finished,
        )

    def _sync_finished(self) -> None:
        self.syncing = False
        self.sync_button.setEnabled(True)

    def _sync_success(self, shop: dict) -> None:
        self.shop = shop
        self.retry_attempt = 0
        self._set_connection("Connected", "Automatic background checks are active.")
        self.last_sync_value.setText(self._format_timestamp(shop["fetched_at"]))
        self._update_cloud_state()
        self.evaluate_matches()

        if shop.get("cloud_pairing_lost"):
            self.activity_label.setText("Shop saved locally. Pair this device again to sync.")
        elif shop.get("cloud_sync_pending"):
            self.activity_label.setText("Shop saved locally. Cloud sync will retry automatically.")
        else:
            self.activity_label.setText("Shop synced. Open the website to view it.")

        delay = max(30, shop.get("seconds_remaining", 0) + random.randint(20, 90))
        self._schedule_sync(delay)

    def _sync_error(self, message: str) -> None:
        self.activity_label.setText(message)
        self.retry_attempt += 1
        self._schedule_sync(backoff_seconds(self.retry_attempt))
        if "Reconnect" in message:
            self._set_connection("Reconnect Riot", "Your Riot session needs attention.")
            self._report_reauth_required()
        elif "internet" in message.lower() or "offline" in message.lower():
            self._set_connection("Offline", "VALSHOP will retry when your connection returns.")

    def _report_reauth_required(self) -> None:
        token = self.credentials.device_token()
        if not token:
            return

        async def report() -> None:
            try:
                await CloudClient(settings.API_BASE_URL, token).heartbeat(True)
            except httpx.HTTPError:
                logger.info("Could not report Riot reconnect state to cloud")

        self.run_worker(report, on_error=lambda _message: None)

    def _schedule_sync(self, delay_seconds: int) -> None:
        self.next_sync_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        self.sync_timer.start(delay_seconds * 1_000)
        self._update_next_check()

    def _check_overdue_sync(self) -> None:
        if (
            self.next_sync_at
            and datetime.now(timezone.utc) >= self.next_sync_at
            and not self.syncing
        ):
            self.sync_now()

    def _update_next_check(self) -> None:
        if not self.next_sync_at:
            self.next_check_value.setText("Waiting")
            return
        remaining = max(0, int((self.next_sync_at - datetime.now(timezone.utc)).total_seconds()))
        hours, remainder = divmod(remaining, 3_600)
        minutes, seconds = divmod(remainder, 60)
        local_time = self.next_sync_at.astimezone().strftime("%I:%M %p").lstrip("0")
        if hours:
            countdown = f"{hours}h {minutes}m"
        elif minutes:
            countdown = f"{minutes}m {seconds}s"
        else:
            countdown = f"{seconds}s"
        self.next_check_value.setText(f"{local_time}  -  in {countdown}")

    def evaluate_matches(self) -> None:
        wanted = {item["skin_uuid"] for item in self.store.wishlist()}
        matches = [offer for offer in self.shop.get("offers", []) if offer["uuid"] in wanted]
        if not self.prefs.get("notifications_enabled"):
            return
        for offer in matches:
            if self.store.should_notify(self.shop["rotation_key"], offer["uuid"]):
                self.tray.showMessage(
                    f"{offer['name']} is in your shop",
                    f"{offer['cost']:,} VP - available until the next rotation",
                    self.icon,
                    10_000,
                )

    def _set_connection(self, status: str, detail: str) -> None:
        state = {
            "Connected": "connected",
            "Offline": "offline",
            "Reconnect Riot": "reconnect",
        }.get(status, "reconnect")
        self.status_label.setText(status)
        self.detail_label.setText(detail)
        self.status_dot.setProperty("state", state)
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)
        self.tray_status.setText(status)
        self.tray_reconnect.setVisible(status != "Connected")
        self.connect_button.setText("Reconnect Riot" if self.riot.session else "Connect Riot")

    def _update_account(self) -> None:
        session = self.riot.session
        if not session:
            self.account_value.setText("Not connected")
            return
        puuid = str(session.get("puuid", ""))
        region = str(session.get("region") or session.get("shard") or "Riot").upper()
        safe_id = f"...{puuid[-8:]}" if len(puuid) >= 8 else "Connected account"
        self.account_value.setText(f"{region}  -  {safe_id}")

    def _update_cloud_state(self) -> None:
        paired = bool(self.credentials.device_token())
        self.cloud_pill.setText("Cloud paired" if paired else "Cloud not paired")
        self.pair_button.setText("Website Paired" if paired else "Pair with Website")
        self.pair_button.setEnabled(not paired)

    def _format_timestamp(self, value: str) -> str:
        try:
            return datetime.fromisoformat(value).astimezone().strftime("%b %d, %I:%M %p")
        except (TypeError, ValueError):
            return "Unknown"

    def toggle_startup(self, value: bool) -> None:
        try:
            set_startup(value)
            self.prefs.set("start_with_windows", value)
        except Exception as exc:
            self.show_error(user_error(exc))
            sender = self.sender()
            if isinstance(sender, QCheckBox):
                sender.blockSignals(True)
                sender.setChecked(False)
                sender.blockSignals(False)

    def test_notification(self) -> None:
        self.tray.showMessage(
            "VALSHOP notifications are ready",
            "You will be notified when a wishlist skin appears.",
            self.icon,
            7_000,
        )

    def check_updates(self) -> None:
        if not settings.UPDATE_METADATA_URL:
            self.show_error("Update checking is not configured for this build.")
            return

        async def check() -> dict | None:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(settings.UPDATE_METADATA_URL)
                response.raise_for_status()
                data = response.json()
            return data if Version(data["version"]) > Version(__version__) else None

        def result(data: dict | None) -> None:
            if not data:
                QMessageBox.information(self, "VALSHOP", "You are running the latest version.")
                return
            box = QMessageBox(self)
            box.setWindowTitle("Update available")
            box.setText(f"VALSHOP {data['version']} is available.")
            download = box.addButton("Download Update", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() == download:
                webbrowser.open(data.get("url") or settings.UPDATE_DOWNLOAD_URL)

        self.run_worker(check, result)

    def show_onboarding(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Welcome to VALSHOP Companion")
        dialog.setFixedSize(500, 360)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(34, 32, 34, 28)
        layout.setSpacing(14)
        brand = QLabel("VALSHOP")
        brand.setObjectName("Brand")
        layout.addWidget(brand)
        title = QLabel("Your shop, checked quietly.")
        title.setObjectName("Title")
        layout.addWidget(title)
        copy = QLabel(
            "The website is your main VALSHOP experience. This companion securely "
            "connects Riot, checks new rotations, syncs them to the website, and "
            "shows native Windows notifications."
        )
        copy.setObjectName("Muted")
        copy.setWordWrap(True)
        layout.addWidget(copy)
        startup = QCheckBox("Start VALSHOP Companion with Windows")
        startup.setChecked(False)
        layout.addWidget(startup)
        layout.addStretch()
        actions = QHBoxLayout()
        later = QPushButton("Not now")
        connect = QPushButton("Connect Riot")
        connect.setObjectName("Primary")
        actions.addWidget(later)
        actions.addStretch()
        actions.addWidget(connect)
        layout.addLayout(actions)

        def finish(connect_riot: bool) -> None:
            if startup.isChecked():
                self.toggle_startup(True)
            self.prefs.set("onboarding_complete", True)
            dialog.accept()
            if connect_riot:
                self.connect_riot()

        later.clicked.connect(lambda: finish(False))
        connect.clicked.connect(lambda: finish(True))
        dialog.exec()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_website()

    def show_error(self, message: str) -> None:
        QMessageBox.warning(self, "VALSHOP Companion", message)

    def closeEvent(self, event) -> None:
        if self._quitting:
            event.accept()
            return
        event.ignore()
        self.hide()
        if not self.prefs.get("close_notice_shown"):
            self.tray.showMessage(
                "VALSHOP Companion is still running",
                "Background shop checks will continue from the system tray.",
                self.icon,
                7_000,
            )
            self.prefs.set("close_notice_shown", True)

    def quit_app(self) -> None:
        self._quitting = True
        self.sync_timer.stop()
        self.wake_timer.stop()
        self.clock_timer.stop()
        self.tray.hide()
        QApplication.quit()


def run_desktop() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("VALSHOP Companion")
    app.setApplicationVersion(__version__)
    app.setStyleSheet(STYLE)
    window = MainWindow()
    if "--minimized" not in sys.argv and not window.prefs.get("launch_minimized"):
        window.show()
    if os.environ.get("VALSHOP_SMOKE_TEST") == "1":
        QTimer.singleShot(1_500, window.close)
        QTimer.singleShot(3_000, window.quit_app)
    return app.exec()
