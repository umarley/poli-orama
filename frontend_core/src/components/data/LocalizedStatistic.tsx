import { Statistic } from 'antd';
import type { StatisticProps } from 'antd';

export function LocalizedStatistic(props: StatisticProps) {
  return <Statistic {...props} groupSeparator="." decimalSeparator="," />;
}
