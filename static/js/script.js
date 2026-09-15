document.addEventListener('DOMContentLoaded', () => {
    document.body.classList.add('page-ready');

    document.querySelectorAll('.option-row').forEach((row) => {
        row.addEventListener('click', () => {
            const input = row.querySelector('input');
            input.checked = true;
            row.classList.remove('option-selected');
            void row.offsetWidth;
            row.classList.add('option-selected');
        });
    });

    document.querySelectorAll('.btn').forEach((button) => {
        button.addEventListener('click', (event) => {
            if (button.disabled) return;
            const ripple = document.createElement('span');
            ripple.className = 'button-ripple';
            const bounds = button.getBoundingClientRect();
            ripple.style.left = `${event.clientX - bounds.left}px`;
            ripple.style.top = `${event.clientY - bounds.top}px`;
            button.appendChild(ripple);
            button.classList.add('button-pressed');
            window.setTimeout(() => button.classList.remove('button-pressed'), 180);
            window.setTimeout(() => ripple.remove(), 500);
        });
    });

    const form = document.querySelector('#question-form');
    if (form) {
        form.addEventListener('submit', (event) => {
            const submitButton = event.submitter;
            const isNextAction = submitButton && submitButton.value === 'next';
            if (isNextAction && !form.querySelector('input[name="answer"]:checked')) {
                event.preventDefault();
                form.classList.add('needs-answer');
                window.setTimeout(() => form.classList.remove('needs-answer'), 450);
                return;
            }
            if (submitButton) submitButton.classList.add('is-submitting');
            form.classList.add('is-submitting');
        });
    }
});