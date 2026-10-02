// Node 20 compatibility polyfill for jsdom 30 / undici 8
const wt = require('node:worker_threads');
if (typeof wt.markAsUncloneable !== 'function') {
  wt.markAsUncloneable = (x) => x;
}
