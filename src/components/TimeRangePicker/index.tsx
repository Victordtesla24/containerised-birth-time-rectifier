import React from 'react';
// @ts-ignore - Ignore the CSS module type error
import styles from './TimeRangePicker.module.css';

interface TimeRange {
  startTime: string;
  endTime: string;
}

interface TimeRangePickerProps {
  value: TimeRange;
  onChange: (value: TimeRange) => void;
  disabled?: boolean;
}

const TimeRangePicker: React.FC<TimeRangePickerProps> = ({
  value,
  onChange,
  disabled = false
}) => {
  const handleStartTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newStartTime = e.target.value;
    onChange({
      ...value,
      startTime: newStartTime
    });
  };

  const handleEndTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newEndTime = e.target.value;
    onChange({
      ...value,
      endTime: newEndTime
    });
  };

  return (
    <div className={styles.container}>
      <div className={styles.timeInputGroup}>
        <label htmlFor="startTime" className={styles.label}>From</label>
        <input
          type="time"
          id="startTime"
          value={value.startTime}
          onChange={handleStartTimeChange}
          disabled={disabled}
          className={styles.timeInput}
          data-testid="time-range-start"
        />
      </div>

      <div className={styles.separator}>to</div>

      <div className={styles.timeInputGroup}>
        <label htmlFor="endTime" className={styles.label}>To</label>
        <input
          type="time"
          id="endTime"
          value={value.endTime}
          onChange={handleEndTimeChange}
          disabled={disabled}
          className={styles.timeInput}
          data-testid="time-range-end"
        />
      </div>
    </div>
  );
};

export default TimeRangePicker;
