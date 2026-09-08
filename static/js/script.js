document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.option-row').forEach((row) => {
        row.addEventListener('click', () => {
            const input = row.querySelector('input');
            input.checked = true;
        });
    });
});