function showToast(type, title, message) {
    var wrapper = document.getElementById('toastWrapper');
    var icons   = { success: '✅', error: '❌' };
    var toast   = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.innerHTML =
        '<div class="toast-icon">' + icons[type] + '</div>' +
        '<div class="toast-body">' +
            '<div class="toast-title">' + title + '</div>' +
            '<div class="toast-msg">' + message + '</div>' +
        '</div>' +
        '<button class="toast-close" onclick="dismissToast(this.parentElement)">✕</button>' +
        '<div class="toast-progress"></div>';
    wrapper.appendChild(toast);
    setTimeout(function() { dismissToast(toast); }, 4000);
}

function dismissToast(toast) {
    if (!toast || !toast.parentElement) return;
    toast.style.animation = 'toastOut 0.4s ease forwards';
    setTimeout(function() { toast.remove(); }, 400);
}

var pendingUserId = null;

function showDeleteModal(userId, name, email) {
    pendingUserId = userId;
    document.getElementById('delName').textContent  = name;
    document.getElementById('delEmail').textContent = email;
    var overlay = document.getElementById('userDeleteOverlay');
    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

document.addEventListener('DOMContentLoaded', function() {

    var flash = document.getElementById('flashData');
    if (flash) {
        if (flash.dataset.success) showToast('success', 'Success!', flash.dataset.success);
        if (flash.dataset.error)   showToast('error',   'Error!',   flash.dataset.error);
    }

    var overlay = document.createElement('div');
    overlay.id = 'userDeleteOverlay';
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
        '<div style="background:#ffffff;border-radius:12px;padding:30px;max-width:420px;width:90%;',
        'box-shadow:0 25px 50px rgba(0,0,0,0.5);margin:auto;">',

        '<h2 style="margin:0 0 10px 0;font-size:20px;font-weight:700;">⚠️ Delete User</h2>',
        '<p style="color:#64748b;margin-bottom:15px;font-size:14px;">',
        'Are you sure you want to delete this staff user?</p>',

        '<div style="background:#fef2f2;padding:15px;border-radius:8px;border-left:4px solid #ef4444;margin-bottom:20px;">',
        '<p style="margin:0 0 6px 0;font-size:14px;"><strong>Name:</strong> <span id="delName"></span></p>',
        '<p style="margin:0;font-size:14px;"><strong>Email:</strong> <span id="delEmail"></span></p>',
        '</div>',

        '<div style="display:flex;gap:10px;justify-content:flex-end;">',
        '<button id="cancelUserDeleteBtn" type="button" style="padding:10px 22px;background:#64748b;',
        'color:#fff;border:none;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;">Cancel</button>',
        '<button id="confirmUserDeleteBtn" type="button" style="padding:10px 22px;background:#ef4444;',
        'color:#fff;border:none;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;">Delete User</button>',
        '</div>',

        '<form id="deleteForm" method="POST" style="display:none;"></form>',
        '</div>'
    ].join('');

    document.body.appendChild(overlay);

    function closeUserModal() {
        overlay.style.display = 'none';
        document.body.style.overflow = '';
        pendingUserId = null;
    }

    document.addEventListener('click', function(e) {
        if (e.target.id === 'confirmUserDeleteBtn') {
            if (!pendingUserId) return;
            var form = document.getElementById('deleteForm');
            form.action = '/admin/users/delete/' + pendingUserId;
            form.style.display = 'block';
            form.submit();
        }
        if (e.target.id === 'cancelUserDeleteBtn' || e.target === overlay) {
            closeUserModal();
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeUserModal();
    });
});