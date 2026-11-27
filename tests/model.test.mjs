import {test} from 'node:test';
import assert from 'node:assert/strict';
import {transferEstimate} from '../web/model.mjs';

test('transfer-only estimates use decimal kilobits, preserve zero and suppress missing observations',()=>{
  assert.equal(transferEstimate(7000,56),'1.0 s');
  assert.equal(transferEstimate(7000,14.4),'3.9 s');
  assert.equal(transferEstimate(840000,56),'2.0 min');
  assert.equal(transferEstimate(0,56),'0.0 s');
  for (const bytes of [null,undefined,'',-1,'unknown']) assert.equal(transferEstimate(bytes,56),'Unavailable');
  assert.equal(transferEstimate(7000,0),'Unavailable');
});
