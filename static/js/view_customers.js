function liveSearchTable(query) {
    var rows        = document.querySelectorAll('.customer-row');
    var noResults   = document.getElementById('noResults');
    var searchCount = document.getElementById('searchCount');
    var pagination  = document.getElementById('paginationWrapper');
    var q = query.toLowerCase().trim();
    var visibleCount = 0;

    rows.forEach(function(row) {
        var name    = row.getAttribute('data-name')    || '';
        var phone   = row.getAttribute('data-phone')   || '';
        var email   = row.getAttribute('data-email')   || '';
        var account = row.getAttribute('data-account') || '';
        var matches = name.includes(q) || phone.includes(q) || email.includes(q) || account.includes(q);
        row.style.display = matches ? '' : 'none';
        if (matches) visibleCount++;
    });

    noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    if (pagination) pagination.style.display = q.length > 0 ? 'none' : 'flex';

    if (q.length > 0) {
        searchCount.textContent = visibleCount + ' result' + (visibleCount !== 1 ? 's' : '') + ' found';
        searchCount.style.color = visibleCount === 0 ? 'var(--danger)' : 'var(--success)';
    } else {
        searchCount.textContent = document.querySelectorAll('.customer-row').length + ' customers';
        searchCount.style.color = 'var(--gray)';
    }
}

var pendingDeleteId = null;

document.addEventListener('DOMContentLoaded', function() {

    var overlay = document.createElement('div');
    overlay.id = 'deleteOverlay';
    overlay.style.cssText = [
        'display:none',
        'position:fixed',
        'top:0', 'left:0', 'right:0', 'bottom:0',
        'width:100%', 'height:100%',
        'background-color:rgba(0,0,0,0.65)',
        'z-index:999999',
        'align-items:center',
        'justify-content:center'
    ].join(';');

    overlay.innerHTML = [
        '<div style="background:#ffffff;border-radius:12px;padding:30px;max-width:450px;width:90%;',
        'box-shadow:0 25px 50px rgba(0,0,0,0.5);margin:auto;">',

        '<div style="display:flex;align-items:center;gap:15px;margin-bottom:20px;">',
        '<div style="width:50px;height:50px;background:rgba(239,68,68,0.12);border-radius:50%;',
        'display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;">⚠️</div>',
        '<h2 style="font-size:21px;font-weight:700;color:#1e293b;margin:0;">Confirm Deletion</h2>',
        '</div>',

        '<p style="font-size:14px;color:#64748b;margin-bottom:15px;">',
        'Are you sure you want to delete this customer? This action cannot be undone.</p>',

        '<div style="background:#f8fafc;padding:15px;border-radius:8px;border-left:4px solid #ef4444;margin-bottom:15px;">',
        '<div style="font-size:14px;color:#1e293b;margin-bottom:6px;">',
        '<strong style="color:#2563eb;">Name:</strong> <span id="deleteName"></span></div>',
        '<div style="font-size:14px;color:#1e293b;">',
        '<strong style="color:#2563eb;">Account:</strong> <span id="deleteAccount"></span></div>',
        '</div>',

        '<p style="font-size:13px;color:#ef4444;font-weight:600;margin-bottom:20px;">',
        '⚠️ All related data (address, nominees, KYC) will be permanently deleted.</p>',

        '<div style="display:flex;gap:10px;justify-content:flex-end;">',
        '<button id="cancelDeleteBtn" type="button" style="padding:10px 22px;background:#64748b;',
        'color:#fff;border:none;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;">Cancel</button>',
        '<button id="confirmDeleteBtn" type="button" style="padding:10px 22px;background:#ef4444;',
        'color:#fff;border:none;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;">Delete Customer</button>',
        '</div>',

        '<form id="deleteForm" method="POST" style="display:none;"></form>',
        '</div>'
    ].join('');

    document.body.appendChild(overlay);

    document.addEventListener('click', function(e) {
        var btn = e.target.closest('.btn-delete');
        if (!btn) return;
        pendingDeleteId = btn.getAttribute('data-customer-id');
        document.getElementById('deleteName').textContent    = btn.getAttribute('data-name');
        document.getElementById('deleteAccount').textContent = btn.getAttribute('data-account');
        overlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    });

    document.addEventListener('click', function(e) {
        if (e.target.id === 'confirmDeleteBtn') {
            if (!pendingDeleteId) return;
            var form = document.getElementById('deleteForm');
            form.action = '/customer/delete/' + pendingDeleteId;
            form.style.display = 'block';
            form.submit();
        }
        if (e.target.id === 'cancelDeleteBtn' || e.target === overlay) {
            overlay.style.display = 'none';
            document.body.style.overflow = '';
            pendingDeleteId = null;
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            overlay.style.display = 'none';
            document.body.style.overflow = '';
            pendingDeleteId = null;
        }
    });
});