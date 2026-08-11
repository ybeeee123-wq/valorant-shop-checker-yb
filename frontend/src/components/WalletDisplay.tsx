import type { Wallet } from '../types';
import { RadianiteIcon, VPIcon } from './Icons';

export default function WalletDisplay({ wallet }: { wallet: Wallet }) {
  return (
    <div className="wallet" aria-label="Wallet balances">
      <div className="wallet-item" title="Valorant Points">
        <VPIcon className="h-3.5 w-3.5" />
        <strong>{wallet.valorant_points.toLocaleString()}</strong>
        <span>VP</span>
      </div>
      <div className="wallet-item wallet-radianite" title="Radianite Points">
        <RadianiteIcon className="h-3.5 w-3.5" />
        <strong>{wallet.radianite_points.toLocaleString()}</strong>
        <span>RP</span>
      </div>
    </div>
  );
}
