import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
};

export default function LoadingSpinner({
  size = 'md',
  text,
  className = ''
}: LoadingSpinnerProps) {
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className="flex items-center space-x-2">
        <Loader2 className={`animate-spin text-primary-600 ${sizeClasses[size]}`} />
        {text && (
          <span className="text-sm text-gray-600">{text}</span>
        )}
      </div>
    </div>
  );
}