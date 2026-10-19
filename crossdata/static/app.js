'use strict';
document.addEventListener('DOMContentLoaded', () => {
  const menu = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  menu?.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
  });
  document.addEventListener('click', event => {
    if (sidebar?.classList.contains('open') && !sidebar.contains(event.target) && !menu.contains(event.target)) {
      sidebar.classList.remove('open'); menu.setAttribute('aria-expanded', 'false');
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && sidebar) { sidebar.classList.remove('open'); menu?.setAttribute('aria-expanded','false'); }
  });
  document.querySelectorAll('.confirm-delete').forEach(form => form.addEventListener('submit', event => {
    if (!window.confirm('¿Eliminar este registro? Se conservará la auditoría y se bloqueará la acción si tiene vínculos.')) event.preventDefault();
  }));
  document.getElementById('print-report')?.addEventListener('click', () => window.print());
  const form = document.getElementById('record-form');
  const alerts = document.getElementById('business-alerts');
  if (!form || !alerts) return;
  const normalize = value => (value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
  const read = id => normalize(document.getElementById(id)?.value);
  const evaluate = () => {
    const messages = [];
    const health = read('data_type').includes('salud');
    if (health) {
      const sensitive = document.getElementById('sensitive');
      const category = document.getElementById('category');
      if (sensitive) sensitive.checked = true;
      if (category) category.value = 'Especial / sensible';
      messages.push('Dato de salud: categoría especial / sensible. Requiere revisión reforzada.');
    }
    if (read('secondary_purpose') && read('secondary_purpose') !== read('purpose')) messages.push('Nueva finalidad: verificar compatibilidad y base jurídica');
    if (health && (read('purpose') + ' ' + read('secondary_purpose')).includes('publicidad')) messages.push('Categoría especial y nueva finalidad: requiere revisión reforzada');
    if (document.getElementById('mechanism') && ['', 'por verificar', 'pendiente'].includes(read('mechanism'))) messages.push('Transferencia pendiente de evaluación');
    alerts.replaceChildren(...messages.map(message => {
      const box = document.createElement('div'); box.className = 'alert alert-warning'; box.textContent = message; return box;
    }));
  };
  form.addEventListener('input', evaluate);
  evaluate();
});
