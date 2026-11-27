import {transferEstimate} from './model.mjs';

const group = document.getElementById('group');
const result = document.getElementById('result');
const rate = document.getElementById('rate');
const rows = [...document.querySelectorAll('tbody tr[data-group]')];

function render() {
  let visible = 0;
  for (const row of rows) {
    row.hidden = Boolean((group.value && row.dataset.group !== group.value) || (result.value && row.dataset.outcome !== result.value));
    if (!row.hidden) visible++;
    const metric = row.querySelector('[data-encoded]');
    metric.textContent = transferEstimate(metric.dataset.encoded,rate.value);
  }
  document.getElementById('rate-label').textContent=rate.value;
  document.getElementById('summary').textContent = visible ? 'Showing '+visible+' of '+rows.length+' tasks.' : 'No tasks match these filters.';
}
for (const select of [group,result,rate]) select.addEventListener('change', render);
document.getElementById('controls').hidden=false;
render();
