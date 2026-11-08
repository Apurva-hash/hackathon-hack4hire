import React, { useState } from 'react';
import { Modal } from './Modal';
import { Button } from './Button';
import { Badge } from './Badge';
import { api } from '../../services/apiClient';
import { useToast } from './Toast';
import { CheckIcon, AlertTriangleIcon } from './Icons';

export interface DemoPaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  bookingId: string;
  amount: number;
  serviceName?: string;
  onPaymentSuccess: (paymentData: any) => void;
}

export const DemoPaymentModal: React.FC<DemoPaymentModalProps> = ({
  isOpen,
  onClose,
  bookingId,
  amount,
  serviceName = 'Home Service',
  onPaymentSuccess,
}) => {
  const { success, error: toastError } = useToast();

  const [selectedMethod, setSelectedMethod] = useState<'cash' | 'gpay' | 'phonepe'>('gpay');
  const [simulationMode, setSimulationMode] = useState<'success' | 'failed'>('success');
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentResult, setPaymentResult] = useState<{
    status: 'completed' | 'failed' | 'pending';
    transaction_id?: string;
    message?: string;
    admin_share?: number;
    technician_share?: number;
    paid_at?: string;
  } | null>(null);

  const handleProcessPayment = async () => {
    setIsProcessing(true);
    // Add realistic 1-second simulated network latency
    await new Promise((resolve) => setTimeout(resolve, 1000));

    try {
      const res = await api.customer.payBooking(bookingId, {
        payment_method: selectedMethod,
        simulate_status: simulationMode,
      });

      if (res.status === 'failed') {
        setPaymentResult({
          status: 'failed',
          message: res.message || 'Payment simulation failed',
          transaction_id: res.transaction_id,
        });
        toastError('Payment Declined', res.message || 'Payment simulation failed');
      } else {
        setPaymentResult(res);
        if (selectedMethod === 'cash') {
          success('Cash on Delivery Selected', 'Pay cash to technician upon job completion.');
        } else {
          success('Payment Successful!', `Transaction ID: ${res.transaction_id}`);
        }
        onPaymentSuccess(res);
      }
    } catch (err: any) {
      toastError('Payment Error', err.message);
      setPaymentResult({
        status: 'failed',
        message: err.message || 'Failed to communicate with payment server',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setPaymentResult(null);
    setIsProcessing(false);
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        handleReset();
        onClose();
      }}
      title={
        paymentResult?.status === 'completed'
          ? 'Payment Confirmation'
          : paymentResult?.status === 'failed'
          ? 'Payment Unsuccessful'
          : 'Select Payment Method'
      }
      description={
        paymentResult?.status === 'completed'
          ? 'Your demo payment transaction is confirmed.'
          : 'Choose your preferred payment method to complete this booking.'
      }
      size="md"
    >
      {/* ── SUCCESS SCREEN ─────────────────────────────────────────────────── */}
      {paymentResult?.status === 'completed' ? (
        <div className="space-y-4 py-2 text-center animate-slide-up">
          <div className="w-16 h-16 rounded-full bg-status-success/10 text-status-success flex items-center justify-center mx-auto shadow-warmSm border border-status-success/30">
            <CheckIcon size={32} />
          </div>

          <div>
            <h3 className="text-xl font-bold text-text">₹{amount} Paid Successfully</h3>
            <p className="text-xs text-text-muted mt-1">
              {selectedMethod === 'cash' ? 'Cash on Delivery Recorded' : 'Verified Demo UPI Transaction'}
            </p>
          </div>

          {/* Receipt card */}
          <div className="p-4 rounded-card bg-surface-alt border border-border text-left space-y-2.5 text-xs">
            <div className="flex justify-between items-center pb-2 border-b border-border">
              <span className="text-text-muted">Transaction ID</span>
              <span className="font-mono font-bold text-text text-[11px]">
                {paymentResult.transaction_id}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Payment Method</span>
              <span className="font-bold uppercase text-text">
                {selectedMethod === 'gpay'
                  ? 'Google Pay (GPay)'
                  : selectedMethod === 'phonepe'
                  ? 'PhonePe UPI'
                  : 'Cash on Delivery'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Service</span>
              <span className="font-medium text-text">{serviceName}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Time</span>
              <span className="text-text-muted">
                {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            </div>
            {/* Revenue share preview */}
            <div className="pt-2 border-t border-border/80 flex justify-between text-[11px]">
              <span className="text-text-muted">Platform Split</span>
              <span className="font-semibold text-primary">
                Tech 60% (₹{paymentResult.technician_share || Math.round(amount * 0.6)}) • Admin 40% (₹{paymentResult.admin_share || Math.round(amount * 0.4)})
              </span>
            </div>
          </div>

          <Button
            variant="primary"
            size="lg"
            onClick={() => {
              handleReset();
              onClose();
            }}
            className="w-full mt-2 min-h-[46px] font-bold"
          >
            Continue to Live Tracking →
          </Button>
        </div>
      ) : paymentResult?.status === 'failed' ? (
        /* ── FAILED SCREEN ─────────────────────────────────────────────────── */
        <div className="space-y-4 py-2 text-center animate-slide-up">
          <div className="w-16 h-16 rounded-full bg-status-error/10 text-status-error flex items-center justify-center mx-auto shadow-warmSm border border-status-error/30">
            <AlertTriangleIcon size={32} />
          </div>

          <div>
            <h3 className="text-xl font-bold text-status-error">Demo Payment Failed</h3>
            <p className="text-xs text-text-muted mt-1 max-w-sm mx-auto">
              {paymentResult.message || 'Simulated bank timeout or UPI pin decline.'}
            </p>
          </div>

          <div className="flex flex-col gap-2 pt-2">
            <Button
              variant="primary"
              size="md"
              onClick={() => {
                setSimulationMode('success');
                handleReset();
              }}
              className="w-full font-bold"
            >
              Try Again with Simulated Success
            </Button>
            <Button
              variant="secondary"
              size="md"
              onClick={() => {
                setSelectedMethod('cash');
                handleReset();
              }}
              className="w-full"
            >
              Switch to Cash on Delivery
            </Button>
          </div>
        </div>
      ) : (
        /* ── PAYMENT METHOD SELECTION & SIMULATOR ──────────────────────────── */
        <div className="space-y-4 py-1">
          {/* Amount banner */}
          <div className="p-3.5 rounded-card bg-primary-tint/20 border border-primary/30 flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold uppercase text-primary tracking-wider">
                Total Amount Due
              </span>
              <div className="text-xs font-bold text-text mt-0.5">{serviceName}</div>
            </div>
            <div className="text-2xl font-bold text-text">₹{amount}</div>
          </div>

          {/* 3 Payment Options */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold uppercase tracking-wider text-text-muted block">
              Choose Payment Method
            </label>

            {/* Google Pay */}
            <div
              onClick={() => setSelectedMethod('gpay')}
              className={`p-3.5 rounded-card border-2 cursor-pointer transition-all flex items-center justify-between ${
                selectedMethod === 'gpay'
                  ? 'border-[#1a73e8] bg-[#1a73e8]/5 shadow-warmSm'
                  : 'border-border bg-surface hover:bg-surface-alt'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white border border-border flex items-center justify-center font-bold text-sm shadow-warmSm">
                  <span className="text-[#4285F4] text-lg font-black">G</span>
                  <span className="text-[#34A853] font-bold text-xs">Pay</span>
                </div>
                <div>
                  <div className="text-xs font-bold text-text flex items-center gap-1.5">
                    <span>Google Pay (GPay)</span>
                    <Badge variant="progress" size="sm">UPI Instant</Badge>
                  </div>
                  <div className="text-[11px] text-text-muted mt-0.5">
                    Fast & secure demo UPI simulation
                  </div>
                </div>
              </div>
              <input
                type="radio"
                name="pay_method"
                checked={selectedMethod === 'gpay'}
                onChange={() => setSelectedMethod('gpay')}
                className="text-[#1a73e8] focus:ring-[#1a73e8]"
              />
            </div>

            {/* PhonePe */}
            <div
              onClick={() => setSelectedMethod('phonepe')}
              className={`p-3.5 rounded-card border-2 cursor-pointer transition-all flex items-center justify-between ${
                selectedMethod === 'phonepe'
                  ? 'border-[#5f259f] bg-[#5f259f]/5 shadow-warmSm'
                  : 'border-border bg-surface hover:bg-surface-alt'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#5f259f] text-white flex items-center justify-center font-bold text-lg shadow-warmSm">
                  पे
                </div>
                <div>
                  <div className="text-xs font-bold text-text flex items-center gap-1.5">
                    <span>PhonePe</span>
                    <Badge variant="progress" size="sm">UPI Instant</Badge>
                  </div>
                  <div className="text-[11px] text-text-muted mt-0.5">
                    Signature PhonePe demo UPI payment
                  </div>
                </div>
              </div>
              <input
                type="radio"
                name="pay_method"
                checked={selectedMethod === 'phonepe'}
                onChange={() => setSelectedMethod('phonepe')}
                className="text-[#5f259f] focus:ring-[#5f259f]"
              />
            </div>

            {/* Cash on Delivery */}
            <div
              onClick={() => setSelectedMethod('cash')}
              className={`p-3.5 rounded-card border-2 cursor-pointer transition-all flex items-center justify-between ${
                selectedMethod === 'cash'
                  ? 'border-status-success bg-status-success/5 shadow-warmSm'
                  : 'border-border bg-surface hover:bg-surface-alt'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-status-success/10 text-status-success border border-status-success/30 flex items-center justify-center font-bold text-lg shadow-warmSm">
                  💵
                </div>
                <div>
                  <div className="text-xs font-bold text-text flex items-center gap-1.5">
                    <span>Cash on Delivery</span>
                    <Badge variant="neutral" size="sm">Pay Later</Badge>
                  </div>
                  <div className="text-[11px] text-text-muted mt-0.5">
                    Pay technician in cash after service completion
                  </div>
                </div>
              </div>
              <input
                type="radio"
                name="pay_method"
                checked={selectedMethod === 'cash'}
                onChange={() => setSelectedMethod('cash')}
                className="text-status-success focus:ring-status-success"
              />
            </div>
          </div>

          {/* ── SIMULATED UPI APP PREVIEW BOX (For GPay / PhonePe) ───────────── */}
          {selectedMethod !== 'cash' && (
            <div
              className={`p-4 rounded-xl border space-y-3 ${
                selectedMethod === 'phonepe'
                  ? 'bg-gradient-to-br from-[#5f259f]/10 to-surface border-[#5f259f]/30'
                  : 'bg-gradient-to-br from-[#1a73e8]/10 to-surface border-[#1a73e8]/30'
              }`}
            >
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-text">
                    {selectedMethod === 'gpay' ? 'Google Pay Gateway' : 'PhonePe Gateway'}
                  </span>
                  <span className="text-[10px] text-text-muted font-mono">
                    {selectedMethod === 'gpay' ? 'dispatchgrid@okhdfc' : 'dispatchgrid@ybl'}
                  </span>
                </div>
                <span className="text-[10px] uppercase font-bold text-primary bg-primary-tint px-2 py-0.5 rounded-full">
                  Demo Mode
                </span>
              </div>

              {/* Simulation Response Selector */}
              <div className="flex items-center justify-between bg-surface p-2.5 rounded-input border border-border text-xs">
                <span className="text-text-muted font-medium">Test Outcome:</span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSimulationMode('success')}
                    className={`px-2.5 py-1 rounded text-[11px] font-bold transition ${
                      simulationMode === 'success'
                        ? 'bg-status-success text-white'
                        : 'bg-surface-alt text-text-muted hover:text-text'
                    }`}
                  >
                    Simulate Success ✓
                  </button>
                  <button
                    type="button"
                    onClick={() => setSimulationMode('failed')}
                    className={`px-2.5 py-1 rounded text-[11px] font-bold transition ${
                      simulationMode === 'failed'
                        ? 'bg-status-error text-white'
                        : 'bg-surface-alt text-text-muted hover:text-text'
                    }`}
                  >
                    Simulate Failure ✕
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-border">
            <Button variant="secondary" size="md" onClick={onClose} disabled={isProcessing}>
              Skip for Now
            </Button>
            <Button
              variant="primary"
              size="lg"
              loading={isProcessing}
              onClick={handleProcessPayment}
              className={`font-bold px-6 min-h-[46px] ${
                selectedMethod === 'phonepe'
                  ? 'bg-[#5f259f] hover:bg-[#4d1d82]'
                  : selectedMethod === 'gpay'
                  ? 'bg-[#1a73e8] hover:bg-[#1557b0]'
                  : 'bg-status-success hover:bg-status-success/90'
              }`}
            >
              {selectedMethod === 'cash'
                ? 'Confirm Cash on Delivery'
                : `Pay ₹${amount} with ${selectedMethod === 'gpay' ? 'GPay' : 'PhonePe'}`}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
};
