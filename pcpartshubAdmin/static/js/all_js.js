//Product script: demo add/edit/delete handlers (fixed) -->

(function(){
  const form = document.getElementById('product-form');
  const tbody = document.querySelector('#products-table tbody');
  const idInput = document.getElementById('prod-id');
  const nameInput = document.getElementById('prod-name');
  const priceInput = document.getElementById('prod-price');
  const stockInput = document.getElementById('prod-stock');
  const categoryInput = document.getElementById('prod-category');
  const shortInput = document.getElementById('prod-short');
  const descInput = document.getElementById('prod-desc');
  const imageInput = document.getElementById('prod-image');
  const preview = document.getElementById('prod-image-preview');
  const addBtn = document.getElementById('btn-open-add');

  // helper: escape HTML for safe insertion
  function escapeHtml(text){
    if(!text) return '';
    return String(text).replace(/[&<>"']/g, function(m){
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m];
    });
  }

  // parse "Rs.45/-" or "£45" -> number
  function parsePriceText(text){
    if(!text) return 0;
    const cleaned = String(text).replace(/[^\d\.\-]/g,'');
    return parseFloat(cleaned) || 0;
  }

  // Format PKR display
  function formatPkr(value){
    if(Number.isInteger(value)) return 'Rs.' + value + '/-';
    return 'Rs.' + value.toFixed(2) + '/-';
  }

  // Open Add modal (clear fields)
  function openAddProduct(){
    form.reset();
    idInput.value = '';
    preview.src = 'assets/img/products/blanket.png';
    // open bootstrap modal
    $('#addProductModal').modal('show');
  }

  // Open Edit modal and populate fields from table row
  function openEditProduct(id){
    const row = tbody.querySelector(`tr[data-id="${id}"]`);
    if(!row) return alert('Product row not found (id='+id+')');

    idInput.value = id;
    nameInput.value = row.children[2].textContent.trim();
    priceInput.value = parsePriceText(row.children[3].textContent);
    stockInput.value = parseInt(row.children[4].textContent) || 0;
    categoryInput.value = row.children[5].textContent.trim();
    shortInput.value = row.children[6].textContent.trim();
    const imgEl = row.children[1].querySelector('img');
    imageInput.value = imgEl ? imgEl.src : '';
    preview.src = imageInput.value || 'assets/img/products/blanket.png';
    $('#addProductModal').modal('show');
  }

  // Add button behaviour
  if(addBtn) addBtn.addEventListener('click', openAddProduct);

  // Live preview for image input
  imageInput.addEventListener('input', ()=> preview.src = imageInput.value || 'assets/img/products/blanket.png');

  // Form submit (create or update)
  form.addEventListener('submit', function(e){
    e.preventDefault();

    // Determine ID: if editing use existing id; if adding compute incremental id
    let id = idInput.value && idInput.value.trim();
    if(!id){
      const rows = Array.from(tbody.querySelectorAll('tr[data-id]'));
      const max = rows.reduce((m, r) => {
        const v = parseInt(r.getAttribute('data-id'), 10);
        return (Number.isFinite(v) && v > m) ? v : m;
      }, 0);
      id = String(max > 0 ? max + 1 : 3001); // start at 3001 if empty
    }

    // Collect values
    const name = nameInput.value.trim();
    const price = parseFloat(priceInput.value) || 0;
    const stock = parseInt(stockInput.value) || 0;
    const category = categoryInput.value || '';
    const shortDesc = shortInput.value.trim();
    const desc = descInput.value.trim();
    const img = imageInput.value.trim() || 'assets/img/products/blanket.png';

    // Build display values
    const displayPrice = formatPkr(price);
    const displayShort = shortDesc || desc;

    const rowHtml = `
      <td>${escapeHtml(id)}</td>
      <td><img src="${escapeHtml(img)}" alt="${escapeHtml(name)}" width="48"></td>
      <td>${escapeHtml(name)}</td>
      <td>${escapeHtml(displayPrice)}</td>
      <td>${escapeHtml(stock)}</td>
      <td>${escapeHtml(category)}</td>
      <td>${escapeHtml(displayShort)}</td>
      <td class="nowrap">
        <button class="btn btn-sm btn-outline-primary btn-edit" data-id="${escapeHtml(id)}">Edit</button>
        <button class="btn btn-sm btn-danger ml-1 admin-only btn-delete" data-id="${escapeHtml(id)}">Delete</button>
      </td>`;

    const existing = tbody.querySelector(`tr[data-id="${id}"]`);
    if(existing){
      existing.innerHTML = rowHtml;
    } else {
      const tr = document.createElement('tr');
      tr.setAttribute('data-id', id);
      tr.innerHTML = rowHtml;
      tbody.appendChild(tr);
    }

    // Close modal and reset
    $('#addProductModal').modal('hide');
    form.reset();
    idInput.value = '';
    preview.src = 'assets/img/products/blanket.png';

  
  });

  // Delegate edit/delete clicks in the table body
  tbody.addEventListener('click', function(e){
    const edit = e.target.closest('.btn-edit');
    const del = e.target.closest('.btn-delete');

    if(edit){
      const id = edit.dataset.id;
      openEditProduct(id);
      return;
    }

    if(del){
      const id = del.dataset.id;
      if(confirm('Delete product #' + id + '?')){
        const row = tbody.querySelector(`tr[data-id="${id}"]`);
        if(row) row.remove();
        // TODO: call backend DELETE endpoint here
      }
      return;
    }
  });

})();


// /*
//   Demo data + handlers for users, orders, and sync with dashboard.
//   This works client-side. Replace with server calls where needed.
// */
// (function(){
//   // -- Demo data -- replace or load from backend
//   const users = [
//     { id: 1, name: 'Fatima', email: 'fatima@example.com', role: 'customer', phone: '0312-111222', notes:'Regular buyer', addresses: [], joined:'2024-05-01' },
//     { id: 2, name: 'Sam', email: 'sam@shop.com', role: 'staff', phone: '0300-222333', notes:'Fulfilment', job:'Inventory Manager', joined:'2023-10-10' },
//     { id: 3, name: 'Ali', email: 'ali@example.com', role: 'customer', phone: '0301-333444', notes:'VIP', joined:'2022-08-02' }
//   ];

//   // orders: each order has id, userId, status, total, date
//   let orders = [
//     { id: 1001, userId: 1, status: 'Processing', total: 45, date:'2025-09-10' },
//     { id: 1000, userId: 3, status: 'Delivered', total: 12, date:'2025-08-20' },
//     { id: 1003, userId: 2, status: 'Processing', total: 60, date:'2025-09-15' },
//     // add a pending example
//     { id: 1004, userId: 1, status: 'Processing', total: 30, date:'2025-09-18' }
//   ];

//   // sample inventory mapping for low-stock calculation (could derive from DOM instead)
//   function computeLowStockCount(){
//     // find <td> with numeric stock in products table
//     const rows = Array.from(document.querySelectorAll('#products-table tbody tr'));
//     let low = 0;
//     rows.forEach(r=>{
//       const stockCell = r.children[4];
//       if(!stockCell) return;
//       const stockNum = parseInt(stockCell.textContent.replace(/[^\d]/g,'')) || 0;
//       const badge = r.querySelector('.badge-low') || null;
//       // if badge exists or stock <=5 treat as low
//       if(badge || stockNum <= 5) low++;
//     });
//     return low;
//   }

//   // ------- rendering functions -------
//   function renderUsers(){
//     const tbody = document.querySelector('#users-table tbody');
//     tbody.innerHTML = '';
//     users.forEach(u=>{
//       const tr = document.createElement('tr');
//       tr.setAttribute('data-id', u.id);
//       tr.innerHTML = `
//         <td>${escapeHtml(u.name)}</td>
//         <td>${escapeHtml(u.email)}</td>
//         <td>${escapeHtml(u.role)}</td>
//         <td class="nowrap">
//           <button class="btn btn-sm btn-outline-primary user-view-btn" data-id="${u.id}">View</button>
//           ${u.role !== 'customer' ? '' : `<button class="btn btn-sm btn-outline-secondary ml-1 user-orders-btn" data-id="${u.id}">Orders</button>`}
//           ${u.role === 'staff' ? `<button class="btn btn-sm btn-info ml-1">Profile</button>` : ''}
//           ${u.role === 'admin' ? `<button class="btn btn-sm btn-danger ml-1 admin-only">Remove</button>` : ''}
//         </td>
//       `;
//       tbody.appendChild(tr);
//     });
//   }

//   function escapeHtml(s){ if(!s) return ''; return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m]); }

//   // open user view modal
//   function openUserView(id){
//     const usr = users.find(u=>u.id==id);
//     if(!usr) return alert('User not found');
//     // fill profile fields
//     document.getElementById('ud-id').value = usr.id;
//     document.getElementById('ud-name').value = usr.name;
//     document.getElementById('ud-email').value = usr.email;
//     document.getElementById('ud-role').value = usr.role || 'customer';
//     document.getElementById('ud-phone').value = usr.phone || '';
//     document.getElementById('ud-notes').value = usr.notes || '';
//     document.getElementById('ud-job').value = usr.job || '';
//     document.getElementById('ud-joined').value = usr.joined || '';

//     // toggle staff/customer panes
//     document.getElementById('staff-info').style.display = usr.role === 'staff' ? '' : 'none';
//     document.getElementById('customer-stats').style.display = usr.role === 'customer' ? '' : 'none';

//     // if customer populate orders
//     if(usr.role === 'customer'){
//       const userOrders = orders.filter(o=>o.userId==usr.id).sort((a,b)=>b.id-a.id);
//       const tbody = document.getElementById('ud-orders-tbody');
//       tbody.innerHTML = '';
//       let totalRevenue = 0;
//       let pendingCount = 0;
//       userOrders.forEach(o=>{
//         totalRevenue += o.total;
//         if(o.status.toLowerCase() === 'processing' || o.status.toLowerCase() === 'pending') pendingCount++;
//         const tr = document.createElement('tr');
//         tr.innerHTML = `<td>${o.id}</td><td>${o.date}</td><td>${escapeHtml(o.status)}</td><td>Rs.${o.total}/-</td>`;
//         tbody.appendChild(tr);
//       });
//       document.getElementById('ud-total-orders').textContent = userOrders.length;
//       document.getElementById('ud-pending-orders').textContent = pendingCount;
//       document.getElementById('ud-total-revenue').textContent = 'Rs.' + totalRevenue + '/-';
//     }

//     $('#userDetailsModal').modal('show');
//   }

//   // save user details from modal
//   document.getElementById('user-details-form').addEventListener('submit', function(e){
//     e.preventDefault();
//     const id = parseInt(document.getElementById('ud-id').value,10);
//     const u = users.find(x=>x.id===id);
//     if(!u) return;
//     u.name = document.getElementById('ud-name').value.trim();
//     u.email = document.getElementById('ud-email').value.trim();
//     u.role = document.getElementById('ud-role').value;
//     u.phone = document.getElementById('ud-phone').value.trim();
//     u.notes = document.getElementById('ud-notes').value.trim();
//     u.job = document.getElementById('ud-job').value.trim();
//     // re-render and close
//     renderUsers();
//     updateDashboard();
//     updateOrdersSidebarBadge();
//     $('#userDetailsModal').modal('hide');
//     // TODO: call backend API to persist user change
//   });

//   // ------- orders rendering and actions -------
//   function renderOrders(){
//     const tbody = document.querySelector('#orders-table tbody');
//     tbody.innerHTML = '';
//     orders.forEach(o=>{
//       const tr = document.createElement('tr');
//       tr.setAttribute('data-id', o.id);
//       // find customer name
//       const user = users.find(u=>u.id===o.userId);
//       tr.innerHTML = `<td>${o.id}</td>
//         <td>${escapeHtml(user ? user.name : 'N/A')}</td>
//         <td>${o.date}</td>
//         <td>Rs.${o.total}/-</td>
//         <td>
//           <select class="form-control form-control-sm status-select">${['Processing','Shipped','Delivered','Cancelled'].map(s=>`<option ${s===o.status?'selected':''}>${s}</option>`).join('')}</select>
//         </td>
//         <td>
//           <button class="btn btn-sm btn-primary order-save" data-id="${o.id}">Save</button>
//           <button class="btn btn-sm btn-outline-secondary ml-1 admin-only order-invoice" data-id="${o.id}">Invoice</button>
//         </td>`;
//       tbody.appendChild(tr);
//     });

//     // attach event handlers for save/invoice/select using delegation
//     tbody.querySelectorAll('.order-save').forEach(btn=>{
//       btn.addEventListener('click', function(){
//         const id = parseInt(this.dataset.id,10);
//         const row = tbody.querySelector(`tr[data-id="${id}"]`);
//         if(!row) return;
//         const sel = row.querySelector('.status-select');
//         const newStatus = sel.value;
//         // update orders array
//         const ord = orders.find(x=>x.id===id);
//         if(ord){
//           ord.status = newStatus;
//         }
//         updateDashboard();
//         renderOrders(); // re-render to refresh UI
//         updateOrdersSidebarBadge();
//         // TODO: save to backend
//       });
//     });

//     tbody.querySelectorAll('.order-invoice').forEach(btn=>{
//       btn.addEventListener('click', function(){
//         const id = parseInt(this.dataset.id,10);
//         alert('Invoice generation placeholder for order #' + id + '. Implement backend invoice generation.');
//       });
//     });
//   }

//   // compute dashboard values from demo data
//   function updateDashboard(){
//   const pending = orders.filter(o => /processing|pending/i.test(o.status)).length;
//   const lowStock = computeLowStockCount();
//   const customReqs = 1;
//   const todaysSales = orders.reduce((acc,o)=> acc + (isToday(o.date) ? parseFloat(o.total) : 0), 0);

//   document.getElementById('pending-count').textContent = pending;
//   document.getElementById('lowstock-count').textContent = lowStock;
//   document.getElementById('custom-count').textContent = customReqs;
//   document.getElementById('todays-sales').textContent = formatPkr(todaysSales);

  
//   setOrdersSidebarBadge(pending);
//     // update recent orders table (dashboard)
//     const recTbody = document.getElementById('recent-orders');
//     if(recTbody){
//       recTbody.innerHTML = '';
//       // show 5 most recent
//       const sorted = orders.slice().sort((a,b)=>b.id-a.id).slice(0,5);
//       sorted.forEach(o=>{
//         const user = users.find(u=>u.id===o.userId);
//         const tr = document.createElement('tr');
//         tr.innerHTML = `<td>${o.id}</td>
//                         <td>${escapeHtml(user ? user.name : 'N/A')}</td>
//                         <td>—</td>
//                         <td>Rs.${o.total}/-</td>
//                         <td><span class="badge ${o.status==='Delivered'?'badge-success':'badge-warning'}">${escapeHtml(o.status)}</span></td>
//                         <td class="nowrap">
//                           <button class="btn btn-sm btn-outline-primary" onclick="openOrder(${o.id})">View</button>
//                         </td>`;
//         recTbody.appendChild(tr);
//       });
//     }
//   }

//   // utility to test date is today (simple)
//   function isToday(d){
//     try{
//       const dd = new Date(d);
//       const now = new Date();
//       return dd.getFullYear()===now.getFullYear() && dd.getMonth()===now.getMonth() && dd.getDate()===now.getDate();
//     }catch(e){ return false; }
//   }

//   // initial render
//   renderUsers();
//   renderOrders();
//   updateDashboard();
//   updateOrdersSidebarBadge();
  

//   // delegate user view clicks
//   document.querySelector('#users-table tbody').addEventListener('click', function(e){
//     const btn = e.target.closest('.user-view-btn');
//     if(btn) {
//       openUserView(parseInt(btn.dataset.id,10));
//     }
//   });

//   // Expose helper to open a user programmatically (useful for other scripts)
//   window.openUserView = function(id){ openUserView(id); };

//   // ---- Role management override: ensure inventory/edit restrictions and order permissions ----
//   // Replace existing setRole function by redefining it (keeps button visuals consistent)
//   window.setRole = function(role){
//     // update pills
//     const roleAdminBtn = document.getElementById('role-admin');
//     const roleStaffBtn = document.getElementById('role-staff');
//     const currentRoleEl = document.getElementById('current-role');
//     if(!roleAdminBtn || !roleStaffBtn || !currentRoleEl) return;
//     if(role==='Admin'){
//       roleAdminBtn.classList.add('btn-primary'); roleAdminBtn.classList.remove('btn-outline-primary');
//       roleStaffBtn.classList.remove('btn-secondary'); roleStaffBtn.classList.add('btn-outline-secondary');
//     } else {
//       roleStaffBtn.classList.add('btn-secondary'); roleStaffBtn.classList.remove('btn-outline-secondary');
//       roleAdminBtn.classList.remove('btn-primary'); roleAdminBtn.classList.add('btn-outline-primary');
//     }
//     currentRoleEl.textContent = role;

//     // admin-only elements
//     document.querySelectorAll('.admin-only').forEach(el=>{
//       if(role==='Admin'){ el.style.display=''; el.classList.remove('disabled-btn'); el.disabled = false; }
//       else { el.style.display='none'; el.classList.add('disabled-btn'); el.disabled = true; }
//     });

//     // actions that staff can see but can't perform (admin-action)
//     document.querySelectorAll('.admin-action').forEach(btn=>{
//       if(role==='Admin'){ btn.classList.remove('disabled-btn'); btn.disabled=false; }
//       else { btn.classList.add('disabled-btn'); btn.disabled=true; }
//     });

//     // Inventory: only Admin may edit stock (buttons usually have class .inventory-edit or admin-only)
//     document.querySelectorAll('#inventory .btn').forEach(btn=>{
//       // mark inventory edit buttons with .inventory-edit if you want fine control — fallback: any delete in inventory becomes admin-only
//       const isDelete = btn.classList.contains('btn-danger') || btn.classList.contains('admin-only');
//       if(role==='Admin'){
//         btn.classList.remove('disabled-btn');
//         btn.disabled = false;
//         if(isDelete) btn.style.display = '';
//       } else {
//         // staff: can't delete / add stock
//         if(isDelete) btn.style.display = 'none';
//         else { btn.classList.add('disabled-btn'); btn.disabled = true; }
//       }
//     });

//     // Orders: staff can change status but cannot generate invoice or delete. We'll disable invoice button for staff.
//     document.querySelectorAll('.order-invoice').forEach(b=>{
//       if(role==='Admin'){ b.style.display=''; b.disabled=false; b.classList.remove('disabled-btn'); }
//       else { b.style.display='none'; b.disabled=true; b.classList.add('disabled-btn'); }
//     });

//     // Users: only admin can remove staff/customer; staff can view but not remove
//     document.querySelectorAll('#users-table .admin-only').forEach(el=>{
//       if(role==='Admin'){ el.style.display=''; el.disabled=false; }
//       else { el.style.display='none'; el.disabled=true; }
//     });

//   };

//   // wire role switch UI
//   document.getElementById('role-admin').addEventListener('click', ()=> setRole('Admin'));
//   document.getElementById('role-staff').addEventListener('click', ()=> setRole('Staff'));
//   // init default
//   setRole('Admin');

// })();

// //--------------------------------------------------------------------------------
//   // Simple role switcher: Admin vs Staff
//   const roleAdminBtn = document.getElementById('role-admin');
//   const roleStaffBtn = document.getElementById('role-staff');
//   const currentRoleEl = document.getElementById('current-role');

//   function setRole(role){
//     // update pill styles
//     if(role==='Admin'){
//       roleAdminBtn.classList.add('btn-primary'); roleAdminBtn.classList.remove('btn-outline-primary');
//       roleStaffBtn.classList.remove('btn-secondary'); roleStaffBtn.classList.add('btn-outline-secondary');
//     } else {
//       roleStaffBtn.classList.add('btn-secondary'); roleStaffBtn.classList.remove('btn-outline-secondary');
//       roleAdminBtn.classList.remove('btn-primary'); roleAdminBtn.classList.add('btn-outline-primary');
//     }
//     currentRoleEl.textContent = role;

//     // show/hide admin-only controls
//     document.querySelectorAll('.admin-only').forEach(el=>{
//       if(role==='Admin'){
//         el.style.display = '';
//         el.classList.remove('disabled-btn');
//       } else {
//         // hide admin-only elements or make them disabled for staff
//         el.style.display = 'none';
//       }
//     });

//     // actions that staff can see but can't perform (example: marked with .admin-action)
//     document.querySelectorAll('.admin-action').forEach(btn=>{
//       if(role==='Admin'){
//         btn.classList.remove('disabled-btn');
//         btn.disabled = false;
//       } else {
//         btn.classList.add('disabled-btn');
//         btn.disabled = true;
//       }
//     });
//   }

//   roleAdminBtn.addEventListener('click',()=>setRole('Admin'));
//   roleStaffBtn.addEventListener('click',()=>setRole('Staff'));

//   // init
//   setRole('Admin');

//   // small helper for opening order details (placeholder)
//   function openOrder(id){
//     alert('Open order details for #' + id + ' — implement modal or page and hook to backend.');
//   }

//--------------------------------------all in 1--------------------------------------
//------------------------------------------------------------------------------------
  (function(){
  /* -----------------------
     Demo data (client-side)
     ----------------------- */
  const products = [
    { id: 3001, name: 'Handmade Baby Blanket', price:45, stock:3, category:'Handmade', short:'Soft merino, 80x80 cm', img:'assets/img/products/pocket.jpg' },
    { id: 3002, name: 'Crochet Keychain - Heart', price:8, stock:15, category:'Keychain', short:'Mini crochet keychain, assorted colors.', img:'assets/img/products/keychain.jpg' }
  ];

  const users = [
    { id: 1, name: 'Fatima', email: 'fatima@example.com', role: 'customer', phone: '0312-111222', notes:'Regular buyer', joined:'2024-05-01' },
    { id: 2, name: 'Sam', email: 'sam@shop.com', role: 'staff', phone: '0300-222333', notes:'Fulfilment', job:'Inventory Manager', joined:'2023-10-10' },
    { id: 3, name: 'Ali', email: 'ali@example.com', role: 'customer', phone: '0301-333444', notes:'VIP', joined:'2022-08-02' }
  ];

  let orders = [
    { id: 1001, userId: 1, status: 'Processing', total: 45, date:'2025-09-10' },
    { id: 1000, userId: 3, status: 'Delivered', total: 12, date:'2025-08-20' },
    { id: 1003, userId: 2, status: 'Processing', total: 60, date:'2025-09-15' },
    { id: 1004, userId: 1, status: 'Processing', total: 30, date:'2025-09-18' }
  ];


  /* -----------------------
     Helpers
     ----------------------- */
  function escapeHtml(s){ if(!s) return ''; return String(s).replace(/[&<>"']/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m]); }
  function formatPkr(v){ return 'Rs.' + (Number.isInteger(v) ? v : v.toFixed(2)) + '/-'; }
  function isToday(d){
    try{ const dd = new Date(d); const now = new Date(); return dd.getFullYear()===now.getFullYear() && dd.getMonth()===now.getMonth() && dd.getDate()===now.getDate(); }
    catch(e){ return false; }
  }

  /* -----------------------
     DOM refs
     ----------------------- */
  const productsTbody = document.querySelector('#products-table tbody');
  const usersTbody = document.querySelector('#users-table tbody');
  const ordersTbody = document.querySelector('#orders-table tbody');
  const recOrdersTbody = document.getElementById('recent-orders');
  const pendingCountEl = document.getElementById('pending-count');
  const lowstockCountEl = document.getElementById('lowstock-count');
  const customCountEl = document.getElementById('custom-count');
  const todaysSalesEl = document.getElementById('todays-sales');
  const ordersBadge = document.getElementById('orders-badge');

  /* -----------------------
     Products: render + handlers
     ----------------------- */
  function renderProducts(){
    if(!productsTbody) return;
    productsTbody.innerHTML = '';
    products.forEach(p=>{
      const tr = document.createElement('tr');
      tr.setAttribute('data-id', p.id);
      const lowBadge = (p.stock <= 5) ? '<span class="badge badge-low ml-2">Low</span>' : '';
      tr.innerHTML = `
        <td>${escapeHtml(p.id)}</td>
        <td><img src="${escapeHtml(p.img)}" alt="${escapeHtml(p.name)}" width="48"></td>
        <td>${escapeHtml(p.name)}</td>
        <td>${formatPkr(p.price)}</td>
        <td>${escapeHtml(p.stock)} ${lowBadge}</td>
        <td>${escapeHtml(p.category)}</td>
        <td>${escapeHtml(p.short)}</td>
        <td class="nowrap">
          <button class="btn btn-sm btn-outline-primary btn-edit" data-id="${p.id}">Edit</button>
          <button class="btn btn-sm btn-danger ml-1 admin-only btn-delete" data-id="${p.id}">Delete</button>
        </td>`;
      productsTbody.appendChild(tr);
    });
  }

  // modal inputs for products (IDs present in your page)
  const pForm = document.getElementById('product-form');
  const pIdEl = document.getElementById('prod-id');
  const pNameEl = document.getElementById('prod-name');
  const pPriceEl = document.getElementById('prod-price');
  const pStockEl = document.getElementById('prod-stock');
  const pCatEl = document.getElementById('prod-category');
  const pShortEl = document.getElementById('prod-short');
  const pDescEl = document.getElementById('prod-desc');
  const pImageEl = document.getElementById('prod-image');
  const pPreview = document.getElementById('prod-image-preview');
  const addProductBtn = document.getElementById('btn-open-add');

  if(addProductBtn) addProductBtn.addEventListener('click', ()=> {
    pForm.reset(); pIdEl.value=''; pPreview.src='assets/img/products/blanket.png';
    $('#addProductModal').modal('show');
  });

  if(pImageEl) pImageEl.addEventListener('input', ()=> pPreview.src = pImageEl.value || 'assets/img/products/blanket.png');

  // incremental ID generator: find max in products array
  function nextProductId(){
    const max = products.reduce((m,p)=> p.id>m?p.id:m, 0);
    return max ? max + 1 : 3001;
  }

  if(pForm){
    pForm.addEventListener('submit', function(e){
      e.preventDefault();
      const editingId = pIdEl.value ? parseInt(pIdEl.value,10) : null;
      const payload = {
        id: editingId || nextProductId(),
        name: pNameEl.value.trim() || 'Untitled',
        price: parseFloat(pPriceEl.value) || 0,
        stock: parseInt(pStockEl.value,10) || 0,
        category: pCatEl.value || '',
        short: pShortEl.value.trim() || pDescEl.value.trim(),
        img: pImageEl.value.trim() || 'assets/img/products/blanket.png'
      };
      if(editingId){
        const idx = products.findIndex(x=>x.id===editingId);
        if(idx>-1) products[idx]=payload;
      } else {
        products.push(payload);
      }
      renderProducts();
      renderOrders(); // in case low-stock changed affecting dashboard
      updateDashboard();
      $('#addProductModal').modal('hide');
      pForm.reset(); pIdEl.value=''; pPreview.src='assets/img/products/blanket.png';
      // TODO: POST/PUT to backend
    });
  }

  // product table delegation
  if(productsTbody){
    productsTbody.addEventListener('click', function(e){
      const edit = e.target.closest('.btn-edit');
      const del = e.target.closest('.btn-delete');
      if(edit){
        const id = parseInt(edit.dataset.id,10);
        const p = products.find(x=>x.id===id);
        if(!p) return alert('Product not found');
        pIdEl.value = p.id;
        pNameEl.value = p.name;
        pPriceEl.value = p.price;
        pStockEl.value = p.stock;
        pCatEl.value = p.category;
        pShortEl.value = p.short;
        pDescEl.value = p.short;
        pImageEl.value = p.img;
        pPreview.src = p.img || 'assets/img/products/blanket.png';
        $('#addProductModal').modal('show');
        return;
      }
      if(del){
        const id = parseInt(del.dataset.id,10);
        if(confirm('Delete product #' + id + '?')){
          const idx = products.findIndex(x=>x.id===id);
          if(idx>-1) products.splice(idx,1);
          renderProducts();
          updateDashboard();
          // TODO: delete on backend
        }
      }
    });
  }

  /* -----------------------
     Users & Orders: render + handlers
     ----------------------- */
  function renderUsers(){
    if(!usersTbody) return;
    usersTbody.innerHTML = '';
    users.forEach(u=>{
      const tr = document.createElement('tr');
      tr.setAttribute('data-id', u.id);
      tr.innerHTML = `
        <td>${escapeHtml(u.name)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${escapeHtml(u.role)}</td>
        <td class="nowrap">
          <button class="btn btn-sm btn-outline-primary user-view-btn" data-id="${u.id}">View</button>
          ${u.role === 'customer' ? `<button class="btn btn-sm btn-outline-secondary ml-1 user-orders-btn" data-id="${u.id}">Orders</button>` : ''}
          ${u.role === 'staff' ? `<button class="btn btn-sm btn-info ml-1">Profile</button>` : ''}
          ${u.role === 'admin' ? `<button class="btn btn-sm btn-danger ml-1 admin-only">Remove</button>` : ''}
        </td>`;
      usersTbody.appendChild(tr);
    });
  }

  function openUserView(id){
    const u = users.find(x=>x.id===id);
    if(!u) return alert('User not found');
    document.getElementById('ud-id').value = u.id;
    document.getElementById('ud-name').value = u.name;
    document.getElementById('ud-email').value = u.email;
    document.getElementById('ud-role').value = u.role || 'customer';
    document.getElementById('ud-phone').value = u.phone || '';
    document.getElementById('ud-notes').value = u.notes || '';
    document.getElementById('ud-job').value = u.job || '';
    document.getElementById('ud-joined').value = u.joined || '';

    document.getElementById('staff-info').style.display = u.role === 'staff' ? '' : 'none';
    document.getElementById('customer-stats').style.display = u.role === 'customer' ? '' : 'none';

    if(u.role === 'customer'){
      const userOrders = orders.filter(o=>o.userId==u.id).sort((a,b)=>b.id-a.id);
      const tbody = document.getElementById('ud-orders-tbody');
      tbody.innerHTML = '';
      let totalRevenue = 0, pending = 0;
      userOrders.forEach(o=>{
        totalRevenue += o.total;
        if(/processing|pending/i.test(o.status)) pending++;
        const r = document.createElement('tr');
        r.innerHTML = `<td>${o.id}</td><td>${o.date}</td><td>${escapeHtml(o.status)}</td><td>${formatPkr(o.total)}</td>`;
        tbody.appendChild(r);
      });
      document.getElementById('ud-total-orders').textContent = userOrders.length;
      document.getElementById('ud-pending-orders').textContent = pending;
      document.getElementById('ud-total-revenue').textContent = formatPkr(totalRevenue);
    }

    $('#userDetailsModal').modal('show');
  }

  // save user modal
  const userDetailsForm = document.getElementById('user-details-form');
  if(userDetailsForm){
    userDetailsForm.addEventListener('submit', function(e){
      e.preventDefault();
      const id = parseInt(document.getElementById('ud-id').value,10);
      const u = users.find(x=>x.id===id);
      if(!u) return;
      u.name = document.getElementById('ud-name').value.trim();
      u.email = document.getElementById('ud-email').value.trim();
      u.role = document.getElementById('ud-role').value;
      u.phone = document.getElementById('ud-phone').value.trim();
      u.notes = document.getElementById('ud-notes').value.trim();
      u.job = document.getElementById('ud-job').value.trim();
      renderUsers();
      updateDashboard();
      $('#userDetailsModal').modal('hide');
      // TODO: persist to backend
    });
  }

  // orders rendering
  function renderOrders(){
    if(!ordersTbody) return;
    ordersTbody.innerHTML = '';
    orders.forEach(o=>{
      const user = users.find(u=>u.id===o.userId);
      const tr = document.createElement('tr');
      tr.setAttribute('data-id', o.id);
      tr.innerHTML = `<td>${o.id}</td>
        <td>${escapeHtml(user ? user.name : 'N/A')}</td>
        <td>${o.date}</td>
        <td>${formatPkr(o.total.replace ? parseFloat(o.total) : o.total)}</td>
        <td>
          <select class="form-control form-control-sm status-select">
            ${['Processing','Shipped','Delivered','Cancelled'].map(s=>`<option ${s===o.status?'selected':''}>${s}</option>`).join('')}
          </select>
        </td>
        <td>
          <button class="btn btn-sm btn-primary order-save" data-id="${o.id}">Save</button>
          <button class="btn btn-sm btn-outline-secondary ml-1 admin-only order-invoice" data-id="${o.id}">Invoice</button>
        </td>`;
      ordersTbody.appendChild(tr);
    });

    // wire save buttons (delegation)
    ordersTbody.querySelectorAll('.order-save').forEach(b=>{
      b.addEventListener('click', function(){
        const id = parseInt(this.dataset.id,10);
        const row = ordersTbody.querySelector(`tr[data-id="${id}"]`);
        if(!row) return;
        const sel = row.querySelector('.status-select');
        const newStatus = sel.value;
        const ord = orders.find(x=>x.id===id);
        if(ord) ord.status = newStatus;
        updateDashboard();
        renderOrders(); // re-render to refresh selects/buttons
        updateOrdersSidebarBadge();

        // TODO: PATCH to backend
      });
    });

    ordersTbody.querySelectorAll('.order-invoice').forEach(b=>{
      b.addEventListener('click', function(){
        const id = parseInt(this.dataset.id,10);
        alert('Invoice placeholder for order #' + id);
      });
    });
  }

  /* -----------------------
     Dashboard + badge sync
     ----------------------- */
  function computeLowStockCount(){
    return products.filter(p => p.stock <= 5).length;
  }

  function getPendingCount(){
    return orders.filter(o => /processing|pending/i.test(String(o.status))).length;
  }

  function updateDashboard(){
    const pending = getPendingCount();
    const low = computeLowStockCount();
    const customReqs = 1;
    const todaysSales = orders.reduce((s,o)=> s + (isToday(o.date) ? Number(o.total) : 0), 0);

    if(pendingCountEl) pendingCountEl.textContent = pending;
    if(lowstockCountEl) lowstockCountEl.textContent = low;
    if(customCountEl) customCountEl.textContent = customReqs;
    if(todaysSalesEl) todaysSalesEl.textContent = formatPkr(todaysSales);

    // recent orders
    if(recOrdersTbody){
      recOrdersTbody.innerHTML = '';
      const sorted = orders.slice().sort((a,b)=>b.id-a.id).slice(0,5);
      sorted.forEach(o=>{
        const user = users.find(u=>u.id===o.userId);
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${o.id}</td>
                        <td>${escapeHtml(user ? user.name : 'N/A')}</td>
                        <td>—</td>
                        <td>${formatPkr(o.total)}</td>
                        <td><span class="badge ${o.status==='Delivered'?'badge-success':'badge-warning'}">${escapeHtml(o.status)}</span></td>
                        <td class="nowrap"><button class="btn btn-sm btn-outline-primary" onclick="openOrder(${o.id})">View</button></td>`;
        recOrdersTbody.appendChild(tr);
      });
    }

    // sidebar badge
    setOrdersSidebarBadge(pending);
  }
   function isToday(d){
    try{
      const dd = new Date(d);
      const now = new Date();
      return dd.getFullYear()===now.getFullYear() && dd.getMonth()===now.getMonth() && dd.getDate()===now.getDate();
    }catch(e){ return false; }
  }


  function setOrdersSidebarBadge(n){
    if(!ordersBadge) return;
    ordersBadge.textContent = n;
    ordersBadge.style.display = (n>0) ? '' : 'none';
  }

  


  /* -----------------------
     Role switcher (single unified)
     ----------------------- */
  function applyRole(role){
    const roleAdminBtn = document.getElementById('role-admin');
    const roleStaffBtn = document.getElementById('role-staff');
    const currentRoleEl = document.getElementById('current-role');
    if(!roleAdminBtn || !roleStaffBtn || !currentRoleEl) return;
    if(role==='Admin'){
      roleAdminBtn.classList.add('btn-primary'); roleAdminBtn.classList.remove('btn-outline-primary');
      roleStaffBtn.classList.remove('btn-secondary'); roleStaffBtn.classList.add('btn-outline-secondary');
    } else {
      roleStaffBtn.classList.add('btn-secondary'); roleStaffBtn.classList.remove('btn-outline-secondary');
      roleAdminBtn.classList.remove('btn-primary'); roleAdminBtn.classList.add('btn-outline-primary');
    }
    currentRoleEl.textContent = role;

    // admin-only controls
    document.querySelectorAll('.admin-only').forEach(el=>{
      if(role==='Admin'){ el.style.display=''; el.disabled=false; el.classList.remove('disabled-btn'); }
      else { el.style.display='none'; el.disabled=true; el.classList.add('disabled-btn'); }
    });

    // admin-action (visible but disabled for staff)
    document.querySelectorAll('.admin-action').forEach(btn=>{
      if(role==='Admin'){ btn.disabled=false; btn.classList.remove('disabled-btn'); }
      else { btn.disabled=true; btn.classList.add('disabled-btn'); }
    });

    // invoices/buttons requiring admin
    document.querySelectorAll('.order-invoice').forEach(b=>{
      if(role==='Admin'){ b.style.display=''; b.disabled=false; b.classList.remove('disabled-btn'); }
      else { b.style.display='none'; b.disabled=true; b.classList.add('disabled-btn'); }
    });

    // Inventory delete buttons
    document.querySelectorAll('#inventory .btn-danger').forEach(b=>{
      if(role==='Admin'){ b.style.display=''; b.disabled=false; b.classList.remove('disabled-btn'); }
      else { b.style.display='none'; b.disabled=true; b.classList.add('disabled-btn'); }
    });

    document.querySelectorAll('#users-table .admin-only').forEach(el=>{
      if(role==='Admin'){ el.style.display=''; el.disabled=false; }
      else { el.style.display='none'; el.disabled=true; }
    });

  }

  // wire role UI buttons (they exist in page)
  const roleAdminBtn = document.getElementById('role-admin');
  const roleStaffBtn = document.getElementById('role-staff');
  if(roleAdminBtn) roleAdminBtn.addEventListener('click', ()=> applyRole('Admin'));
  if(roleStaffBtn) roleStaffBtn.addEventListener('click', ()=> applyRole('Staff'));

  // expose helper for openOrder used in inline onclick
  window.openOrder = function(id){
    // for demo just show details modal or alert
    const ord = orders.find(o=>o.id===id);
    if(!ord) return alert('Order #' + id + ' not found');
    const user = users.find(u=>u.id===ord.userId);
    alert(`Order #${ord.id}\nCustomer: ${user ? user.name : 'N/A'}\nStatus: ${ord.status}\nTotal: ${formatPkr(ord.total)}`);
  };

  /* -----------------------
     Boot: initial render & event wiring

      ----------------------- */
  // Disable all edit buttons when Admin Mode is OFF

  function boot(){
    renderProducts();
    renderUsers();
    renderOrders();
    updateDashboard();
    setOrdersSidebarBadge();
    updateAccess()
    saveTax()
    savePayment()
    savePolicy()
    applyRole('Admin'); // default
    // user view click delegation
    usersTbody && usersTbody.addEventListener('click', function(e){
      const btn = e.target.closest('.user-view-btn');
      if(btn) openUserView(parseInt(btn.dataset.id,10));
    });
  }

  // Start after DOM loaded
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', boot);
  } else boot();

  // Expose updateDashboard for external calls if needed
  window.updateDashboard = updateDashboard;

})();

  document.addEventListener('DOMContentLoaded', function () {
    const adminToggle = document.getElementById('adminToggle');
    const editButtons = document.querySelectorAll('[data-bs-toggle="modal"]');

function updateAccess() {
      const isAdmin = adminToggle.checked;
      editButtons.forEach(btn => {
        btn.disabled = !isAdmin;
      });
    }

    adminToggle.addEventListener('change', updateAccess);
    updateAccess(); // Run on load
  });

function savePayment() {
    document.getElementById('paymentDesc').innerText = document.getElementById('paymentInput').value;
  }
  function saveShipping() {
    document.getElementById('shippingDesc').innerText = document.getElementById('shippingInput').value;
  }
  function saveTax() {
    document.getElementById('taxDesc').innerText = document.getElementById('taxInput').value;
  }
  function savePolicy() {
    document.getElementById('policyDesc').innerText = document.getElementById('policyInput').value;
  }