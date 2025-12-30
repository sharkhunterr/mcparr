import { Activity, Cpu, HardDrive, MemoryStick, Server, Wifi } from 'lucide-react';
import MetricsCard from './MetricsCard';
import type { SystemMetrics } from '../../types/api';

interface MetricsGridProps {
  metrics: SystemMetrics | null;
  loading?: boolean;
}

export default function MetricsGrid({ metrics, loading = false }: MetricsGridProps) {
  if (loading || !metrics) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 6 }).map((_, index) => (
          <MetricsCard
            key={index}
            title="Loading..."
            value="--"
            icon={Activity}
            loading={true}
          />
        ))}
      </div>
    );
  }

  const getCpuTrend = (usage: number) => {
    if (usage < 30) return 'stable';
    if (usage < 70) return 'up';
    return 'down';
  };

  const getMemoryTrend = (usage: number) => {
    if (usage < 60) return 'stable';
    if (usage < 85) return 'up';
    return 'down';
  };

  const getDiskTrend = (usage: number) => {
    if (usage < 70) return 'stable';
    if (usage < 90) return 'up';
    return 'down';
  };

  const cpuUsage = Math.round(metrics.cpu_usage);
  const memoryUsage = Math.round(metrics.memory_usage);
  const diskUsage = Math.round(metrics.disk_usage);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <MetricsCard
        title="CPU Usage"
        value={cpuUsage}
        unit="%"
        icon={Cpu}
        trend={getCpuTrend(cpuUsage)}
        trendValue={`${cpuUsage}%`}
        color={cpuUsage > 80 ? 'danger' : cpuUsage > 60 ? 'warning' : 'success'}
      />

      <MetricsCard
        title="Memory Usage"
        value={memoryUsage}
        unit="%"
        icon={MemoryStick}
        trend={getMemoryTrend(memoryUsage)}
        trendValue={`${(metrics.memory_total / (1024**3)).toFixed(1)}GB`}
        color={memoryUsage > 85 ? 'danger' : memoryUsage > 70 ? 'warning' : 'success'}
      />

      <MetricsCard
        title="Disk Usage"
        value={diskUsage}
        unit="%"
        icon={HardDrive}
        trend={getDiskTrend(diskUsage)}
        trendValue={`${(metrics.disk_total / (1024**3)).toFixed(1)}GB`}
        color={diskUsage > 90 ? 'danger' : diskUsage > 75 ? 'warning' : 'success'}
      />

      <MetricsCard
        title="Network I/O"
        value={(metrics.network_bytes_sent / (1024**2)).toFixed(1)}
        unit="MB/s"
        icon={Wifi}
        trend="up"
        trendValue={`↑${(metrics.network_bytes_recv / (1024**2)).toFixed(1)}MB/s`}
        color="primary"
      />

      <MetricsCard
        title="Active Services"
        value={metrics.services_running}
        icon={Server}
        trend="stable"
        trendValue={`${metrics.services_total} total`}
        color={metrics.services_running === metrics.services_total ? 'success' : 'warning'}
      />

      <MetricsCard
        title="System Load"
        value={metrics.cpu_load_avg.toFixed(2)}
        icon={Activity}
        trend={metrics.cpu_load_avg > 1 ? 'up' : 'stable'}
        trendValue={`${metrics.cpu_load_avg > 1 ? 'High' : 'Normal'}`}
        color={metrics.cpu_load_avg > 2 ? 'danger' : metrics.cpu_load_avg > 1 ? 'warning' : 'success'}
      />
    </div>
  );
}