export function transferEstimate(bytes,rate) {
  if (bytes == null || bytes === '' || !Number.isFinite(Number(bytes)) || Number(bytes)<0 || !Number.isFinite(Number(rate)) || Number(rate)<=0) return 'Unavailable';
  const seconds=Number(bytes)*8/(Number(rate)*1000);
  if (seconds<10) return seconds.toFixed(1)+' s';
  if (seconds<60) return seconds.toFixed(0)+' s';
  return (seconds/60).toFixed(1)+' min';
}
