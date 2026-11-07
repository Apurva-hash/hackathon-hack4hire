import React from 'react';
import { CheckIcon, ClockIcon } from './Icons';

export interface StepItem {
  id: string;
  label: string;
  timestamp?: string;
}

export interface StepperProps {
  steps: StepItem[];
  currentStepId: string;
  className?: string;
}

export const Stepper: React.FC<StepperProps> = ({ steps, currentStepId, className = '' }) => {
  const currentIndex = steps.findIndex((s) => s.id === currentStepId);

  return (
    <div className={`w-full py-4 ${className}`}>
      <div className="flex items-center justify-between relative">
        {/* Connecting Line */}
        <div className="absolute top-4 left-6 right-6 h-0.5 bg-border -z-0" />
        <div
          className="absolute top-4 left-6 h-0.5 bg-primary transition-all duration-300 -z-0"
          style={{
            width: `${
              currentIndex > 0 ? (currentIndex / (steps.length - 1)) * 100 : 0
            }%`,
          }}
        />

        {steps.map((step, index) => {
          const isCompleted = index < currentIndex;
          const isCurrent = index === currentIndex;

          return (
            <div key={step.id} className="flex flex-col items-center relative z-10">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition-colors duration-200 border-2 ${
                  isCompleted
                    ? 'bg-status-success border-status-success text-white'
                    : isCurrent
                    ? 'bg-primary border-primary text-white shadow-warmSm'
                    : 'bg-surface border-border text-text-muted'
                }`}
              >
                {isCompleted ? (
                  <CheckIcon size={16} />
                ) : isCurrent ? (
                  <ClockIcon size={16} />
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>
              <span
                className={`text-xs mt-2 font-semibold text-center max-w-[70px] leading-tight ${
                  isCurrent ? 'text-primary' : isCompleted ? 'text-text' : 'text-text-muted'
                }`}
              >
                {step.label}
              </span>
              {step.timestamp && (
                <span className="text-[10px] text-text-muted mt-0.5">
                  {step.timestamp}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

