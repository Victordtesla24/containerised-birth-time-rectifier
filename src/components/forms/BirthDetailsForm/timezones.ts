import { TimeZone } from './types';

export const timezones: TimeZone[] = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'America/Anchorage', label: 'Alaska Time (AKT)' },
  { value: 'Pacific/Honolulu', label: 'Hawaii-Aleutian Time (HST)' },
  { value: 'Europe/London', label: 'British Time (GMT/BST)' },
  { value: 'Europe/Paris', label: 'Central European Time (CET)' },
  { value: 'Europe/Moscow', label: 'Moscow Time (MSK)' },
  { value: 'Asia/Dubai', label: 'Gulf Time (GST)' },
  { value: 'Asia/Kolkata', label: 'India Time (IST)' },
  { value: 'Asia/Shanghai', label: 'China Time (CST)' },
  { value: 'Asia/Tokyo', label: 'Japan Time (JST)' },
  { value: 'Australia/Sydney', label: 'Australian Eastern Time (AET)' },
  { value: 'Pacific/Auckland', label: 'New Zealand Time (NZT)' },
];

export const getTimezoneOffset = (timezone: string): number => {
  const date = new Date();
  const tzDate = new Date(date.toLocaleString('en-US', { timeZone: timezone }));
  return (tzDate.getTime() - date.getTime()) / (60 * 1000);
}; 