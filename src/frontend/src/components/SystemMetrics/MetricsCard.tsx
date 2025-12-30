import type { FC } from 'react';

interface MetricsCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon: FC<any>;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  color?: 'primary' | 'success' | 'warning' | 'danger';
  loading?: boolean;
}

const colorClasses = {
  primary: 'text-primary-600 bg-primary-100',
  success: 'text-success-600 bg-success-100',
  warning: 'text-warning-600 bg-warning-100',
  danger: 'text-danger-600 bg-danger-100',
};

const trendClasses = {
  up: 'text-success-600',
  down: 'text-danger-600',
  stable: 'text-gray-500',
};

export default function MetricsCard({
  title,
  value,
  unit = '',
  icon: Icon,
  trend,
  trendValue,
  color = 'primary',
  loading = false,
}: MetricsCardProps) {
  if (loading) {
    return (
      <div className="card">
        <div className="card-body">
          <div className="animate-pulse">
            <div className="flex items-center">
              <div className="h-10 w-10 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
              <div className="ml-3 flex-1">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                <div className="mt-2 h-6 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card animate-fade-in hover-lift">
      <div className="card-body">
        <div className="flex items-center">
          <div className={`p-2 rounded-lg transition-colors duration-200 ${colorClasses[color]}`}>
            <Icon className="h-6 w-6" />
          </div>
          <div className="ml-3 flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400 truncate">{title}</p>
            <div className="flex items-baseline space-x-2 flex-wrap">
              <p className="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-white">
                {value}
                {unit && <span className="text-base sm:text-lg text-gray-500 dark:text-gray-400">{unit}</span>}
              </p>
              {trend && trendValue && (
                <span className={`text-xs sm:text-sm transition-colors duration-200 ${trendClasses[trend]}`}>
                  {trend === 'up' ? '↗' : trend === 'down' ? '↘' : '→'}
                  <span className="hidden sm:inline ml-1">{trendValue}</span>
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}