import test, {after, afterEach, beforeEach} from 'node:test';
import assert from 'node:assert/strict';
import {mkdir, readFile, writeFile, rm} from 'node:fs/promises';
import {webcrypto} from 'node:crypto';
import ts from 'typescript';
import {JSDOM} from 'jsdom';

const temporary = new URL('../.test-build/', import.meta.url);
await mkdir(temporary, {recursive:true});
for (const file of ['export', 'App']) {
  const source = await readFile(new URL(`../src/${file}.${file === 'App' ? 'tsx' : 'ts'}`, import.meta.url), 'utf8');
  const transformed = ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.ESNext, target:ts.ScriptTarget.ES2022, jsx:ts.JsxEmit.ReactJSX}});
  await writeFile(new URL(`${file}.mjs`, temporary), transformed.outputText.replace("'./export'", "'./export.mjs'"));
}
const dom = new JSDOM('<!doctype html><html><body></body></html>', {url:'http://stockpilot.local/'});
for (const property of ['window','document','navigator','HTMLElement','HTMLInputElement','MutationObserver','FormData','Event','MouseEvent']) {
  Object.defineProperty(globalThis, property, {value:dom.window[property], configurable:true, writable:true});
}
Object.defineProperty(globalThis, 'crypto', {value:webcrypto, configurable:true});
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const React = await import('react');
const {render, screen, fireEvent, waitFor, cleanup, within} = await import('@testing-library/react');
const {default:App} = await import(new URL('App.mjs', temporary));
const {createRequestKey, inventoryCsv} = await import(new URL('export.mjs', temporary));

const product = {id:1, sku:'KB-104', name:'Mechanical keyboard', category:'Peripherals', price_cents:649900, reorder_point:20, supplier_id:1};
const supplier = {id:1, name:'Circuit Supply Co.', email:'orders@circuit.example', lead_days:3};
const warehouse = {id:1, code:'DEL-01', name:'Delhi distribution', location:'New Delhi'};
const secondWarehouse = {id:2, code:'BLR-02', name:'Bengaluru fulfilment', location:'Bengaluru'};
const dashboard = {product_count:1, on_hand:128, reserved:0, available:128, inventory_value_cents:83187200, open_orders:0, low_stock:[], warehouses:[{name:warehouse.name,units:128},{name:secondWarehouse.name,units:0}], categories:[{name:'Peripherals',units:128}], recent_movements:[]};
let requests;
let overrides;
function response(body, status=200) {return new Response(body===undefined?null:JSON.stringify(body), {status, headers:{'Content-Type':'application/json'}});}
beforeEach(() => {
  window.location.hash = '';
  requests = [];
  overrides = {};
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(url, 'http://stockpilot.local').pathname;
    const method = options.method || 'GET';
    requests.push({path,method,search:new URL(url, 'http://stockpilot.local').searchParams,body:options.body?JSON.parse(options.body):undefined});
    if (overrides[method+' '+path]) return overrides[method+' '+path](requests.at(-1));
    const routes = {
      '/api/products':[product], '/api/suppliers':[supplier], '/api/warehouses':[warehouse,secondWarehouse],
      '/api/inventory':[{...product, product_id:1, warehouse_id:1, warehouse:warehouse.name, warehouse_code:warehouse.code, on_hand:128, reserved:0, available:128}],
      '/api/movements':[], '/api/reservations':[], '/api/purchase-orders':[], '/api/dashboard':dashboard,
    };
    return response(routes[path] ?? {detail:'Unexpected test request'}, path in routes?200:404);
  };
});
afterEach(() => cleanup());
after(async () => {await rm(temporary, {recursive:true,force:true}); dom.window.close();});
async function workspace() {render(React.createElement(App));await screen.findByText('Everything in its right place.');}
function navigate(name) {fireEvent.click(screen.getByRole('button',{name,exact:true}));}

test('request keys support insecure local-cluster HTTP without randomUUID', () => {
  const old = globalThis.crypto;
  Object.defineProperty(globalThis,'crypto',{value:{getRandomValues:array=>old.getRandomValues(array)},configurable:true});
  try {const first=createRequestKey();assert.match(first,/^web-[a-f0-9]{32}$/);assert.notEqual(first,createRequestKey());}
  finally {Object.defineProperty(globalThis,'crypto',{value:old,configurable:true});}
});

test('CSV protects spreadsheet formulas and preserves quotes, commas and line breaks', () => {
  const csv = inventoryCsv([['SKU','Name','Units'],['A-1','=HYPERLINK("x")',12],['A-2','  +SUM(1,2)',5],['A-3','@calc',0],['A-4','\t=SUM(2)',1],['A-5','-cmd',1],['A-6','Safe "desk", large',2]]);
  assert.ok(csv.includes('"\'=HYPERLINK(""x"")"'));
  assert.ok(csv.includes('"\'  +SUM(1,2)"'));
  assert.ok(csv.includes('"\'@calc"'));
  assert.ok(csv.includes('"\'\t=SUM(2)"'));
  assert.ok(csv.includes('"\'-cmd"'));
  assert.ok(csv.includes('"Safe ""desk"", large"'));
  assert.equal(csv.split('\r\n').length,7);
});

test('loads API data into dashboard and supports all eight workspace views', async () => {
  await workspace();
  assert.ok(screen.getByText(/128 units available across 2 warehouses/));
  for (const name of ['Inventory','Movements','Purchase orders','Reservations','Warehouses','Suppliers','Reports']) {
    navigate(name);
    assert.ok(screen.getByRole('heading',{name,level:1}));
  }
  assert.equal(requests.filter(r=>r.method==='GET').length,8);
});

test('shows a server error and can recover by retrying', async () => {
  overrides['GET /api/dashboard'] = () => response({detail:'Database temporarily unavailable'},503);
  render(React.createElement(App));
  assert.ok(screen.getByText('Loading your workspace'));
  assert.ok(await screen.findByText('Database temporarily unavailable'));
  delete overrides['GET /api/dashboard'];
  fireEvent.click(screen.getByRole('button',{name:'Retry'}));
  await screen.findByText('Everything in its right place.');
  assert.equal(screen.queryByText('Database temporarily unavailable'),null);
});

test('product creation sends API schema and converts rupees to integer cents', async () => {
  overrides['POST /api/products'] = () => response({...product,id:2},201);
  await workspace();navigate('Inventory');
  fireEvent.click(screen.getByRole('button',{name:'New product'}));
  const dialog = screen.getByRole('dialog');
  fireEvent.change(within(dialog).getByLabelText('Product name'),{target:{value:'Studio microphone'}});
  fireEvent.change(within(dialog).getByLabelText('SKU'),{target:{value:'au-999'}});
  fireEvent.change(within(dialog).getByLabelText('Unit price (₹)'),{target:{value:'1250.25'}});
  fireEvent.change(within(dialog).getByLabelText('Supplier'),{target:{value:'1'}});
  fireEvent.click(within(dialog).getByRole('button',{name:'Create product'}));
  await waitFor(()=>assert.ok(screen.queryByRole('dialog')===null));
  const request=requests.find(r=>r.method==='POST');
  assert.deepEqual(request.body,{sku:'AU-999',name:'Studio microphone',category:'General',price_cents:125025,reorder_point:10,supplier_id:1});
});

test('transfer retries reuse idempotency keys and show real insufficient-stock error', async () => {
  let attempts=0;
  overrides['POST /api/movements'] = () => ++attempts===1 ? response({detail:'Insufficient available stock; reserved units cannot be moved'},409) : response({id:17},201);
  await workspace();navigate('Movements');
  fireEvent.click(screen.getByRole('button',{name:'Record movement'}));
  const dialog=screen.getByRole('dialog');
  fireEvent.click(within(dialog).getByRole('button',{name:'Transfer'}));
  fireEvent.change(within(dialog).getByLabelText('Product'),{target:{value:'1'}});
  fireEvent.change(within(dialog).getByLabelText('Quantity (units)'),{target:{value:'4'}});
  fireEvent.change(within(dialog).getByLabelText('Reference (optional)'),{target:{value:'MOVE-2026'}});
  fireEvent.click(within(dialog).getByRole('button',{name:'Record movement'}));
  await screen.findByText('Insufficient available stock; reserved units cannot be moved');
  fireEvent.click(within(dialog).getByRole('button',{name:'Record movement'}));
  await waitFor(()=>assert.ok(screen.queryByRole('dialog')===null));
  const mutations=requests.filter(r=>r.method==='POST');
  assert.equal(mutations.length,2);
  assert.equal(mutations[0].body.idempotency_key,mutations[1].body.idempotency_key);
  assert.deepEqual({...mutations[0].body,idempotency_key:undefined},{product_id:1,warehouse_id:1,destination_id:2,kind:'transfer',quantity:4,reference:'MOVE-2026',idempotency_key:undefined});
});

test('purchase order draft form limits lines to selected supplier and submits costs', async () => {
  overrides['POST /api/purchase-orders'] = () => response({id:1,status:'draft'},201);
  await workspace();navigate('Purchase orders');
  fireEvent.click(screen.getByRole('button',{name:'New purchase order'}));
  const dialog=screen.getByRole('dialog');
  assert.equal(within(dialog).getByRole('button',{name:'Add line item'}).disabled,true);
  fireEvent.change(within(dialog).getByLabelText('Quantity'),{target:{value:'25'}});
  fireEvent.change(within(dialog).getByLabelText('Unit cost (₹)'),{target:{value:'5000'}});
  fireEvent.change(within(dialog).getByLabelText('Order note (optional)'),{target:{value:'Monthly restock'}});
  fireEvent.click(within(dialog).getByRole('button',{name:'Save draft'}));
  await waitFor(()=>assert.ok(screen.queryByRole('dialog')===null));
  assert.deepEqual(requests.find(r=>r.method==='POST').body,{supplier_id:1,warehouse_id:1,note:'Monthly restock',items:[{product_id:1,quantity:25,unit_cost_cents:500000}]});
});

test('reports expose unavailable background processing without hiding live inventory', async () => {
  overrides['POST /api/reports'] = () => response({detail:'Background processing is unavailable; live inventory remains accessible'},503);
  await workspace();navigate('Reports');
  fireEvent.click(screen.getByRole('button',{name:'Generate report'}));
  await screen.findByText('Background processing is unavailable; live inventory remains accessible');
  assert.ok(screen.getByText('Live replenishment recommendations'));
});

test('purchase orders move from draft through ordered to received using explicit actions', async () => {
  let status='draft';
  const order={id:7,supplier_id:1,warehouse_id:1,note:'Restock',created_at:'2026-10-16T10:00:00Z',items:[{product_id:1,quantity:10,unit_cost_cents:500000}]};
  overrides['GET /api/purchase-orders']=()=>response([{...order,status}]);
  overrides['POST /api/purchase-orders/7/order']=()=>{status='ordered';return response({...order,status});};
  overrides['POST /api/purchase-orders/7/receive']=()=>{status='received';return response({...order,status});};
  await workspace();navigate('Purchase orders');
  fireEvent.click(screen.getByRole('button',{name:/Place order/}));
  const receive = await screen.findByRole('button',{name:'Receive stock'});
  assert.ok(screen.queryByRole('button',{name:'Edit draft'})===null);
  fireEvent.click(receive);
  await screen.findByText('Order received. Stock updated across all order lines.');
  assert.ok(screen.queryByRole('button',{name:'Receive stock'})===null);
  assert.deepEqual(requests.filter(r=>r.method==='POST').map(r=>r.path),['/api/purchase-orders/7/order','/api/purchase-orders/7/receive']);
});

test('reservations reserve inventory then fulfill through the API', async () => {
  let reservations=[];
  overrides['GET /api/reservations']=()=>response(reservations);
  overrides['POST /api/reservations']=request=>{reservations=[{...request.body,id:3,status:'active',created_at:'2026-10-16T10:00:00Z'}];return response(reservations[0],201);};
  overrides['POST /api/reservations/3/fulfill']=()=>{reservations[0].status='fulfilled';return response(reservations[0]);};
  await workspace();navigate('Reservations');
  fireEvent.click(screen.getByRole('button',{name:'New reservation'}));
  const dialog=screen.getByRole('dialog');
  fireEvent.change(within(dialog).getByLabelText('Product'),{target:{value:'1'}});
  fireEvent.change(within(dialog).getByLabelText('Quantity (units)'),{target:{value:'3'}});
  fireEvent.change(within(dialog).getByLabelText('Order reference'),{target:{value:'CUSTOMER-1042'}});
  fireEvent.click(within(dialog).getByRole('button',{name:'Reserve stock'}));
  const fulfill=await screen.findByRole('button',{name:'Fulfill'});
  assert.ok(screen.getByRole('button',{name:'Release'}));
  fireEvent.click(fulfill);
  await screen.findByText('fulfilled');
  assert.ok(screen.getByText('Closed'));
  const payload=requests.find(r=>r.path==='/api/reservations'&&r.method==='POST').body;
  assert.equal(payload.product_id,1);assert.equal(payload.warehouse_id,1);assert.equal(payload.quantity,3);assert.equal(payload.reference,'CUSTOMER-1042');
  assert.match(payload.idempotency_key,/^web-[a-f0-9-]+$/);
});

test('destructive actions ask for confirmation and display referenced-record conflicts', async () => {
  overrides['DELETE /api/suppliers/1']=()=>response({detail:'Record conflicts with an existing value or referenced inventory history'},409);
  await workspace();navigate('Suppliers');
  fireEvent.click(screen.getByRole('button',{name:'Delete Circuit Supply Co.'}));
  assert.equal(requests.filter(r=>r.method==='DELETE').length,0);
  const dialog=screen.getByRole('dialog');
  fireEvent.click(within(dialog).getByRole('button',{name:'Confirm'}));
  await screen.findByText('Record conflicts with an existing value or referenced inventory history');
  assert.ok(screen.getByRole('dialog'));
  fireEvent.click(within(dialog).getByRole('button',{name:'Keep record'}));
  assert.ok(screen.queryByRole('dialog')===null);
  assert.ok(screen.getByText('Circuit Supply Co.'));
});

test('cached reports show readable snapshot metrics and timestamp', async () => {
  overrides['GET /api/reports/latest']=()=>response({...dashboard,generated_at:'2026-10-16T10:00:00Z'});
  await workspace();navigate('Reports');
  fireEvent.click(screen.getByRole('button',{name:'Load latest snapshot'}));
  await screen.findByText('Background snapshot');
  assert.ok(screen.getByText(/This is a saved snapshot/));
  assert.ok(screen.getByText('Inventory value'));
  assert.ok(screen.getByText('Products to replenish'));
});


test('catalog loads every API page and searches products beyond the first 200 records', async () => {
  const catalog=Array.from({length:205},(_,index)=>({...product,id:index+1,sku:`SKU-${index+1}`,name:`Catalog item ${index+1}`}));
  overrides['GET /api/products']=request=>{const offset=Number(request.search.get('offset'));return response(catalog.slice(offset,offset+200));};
  await workspace();navigate('Inventory');
  fireEvent.change(screen.getByRole('textbox',{name:'Search records'}),{target:{value:'Catalog item 205'}});
  assert.ok(screen.getByText('Catalog item 205'));
  assert.equal(screen.getAllByRole('row').length,2);
  assert.deepEqual(requests.filter(r=>r.path==='/api/products').map(r=>r.search.get('offset')),['0','200']);
});
