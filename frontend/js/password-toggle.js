// Ajoute un bouton afficher/masquer sur chaque champ mot de passe de la
// page (element .password-toggle avec data-target pointant vers l'id du
// champ). Reutilisable sur n'importe quel formulaire (connexion,
// inscription...).

export function initPasswordToggles() {
  document.querySelectorAll('.password-toggle').forEach((button) => {
    const input = document.getElementById(button.dataset.target);
    if (!input) return;

    const eyeIcon = button.querySelector('.icon-eye');
    const eyeOffIcon = button.querySelector('.icon-eye-off');

    button.addEventListener('click', () => {
      const isCurrentlyHidden = input.type === 'password';

      input.type = isCurrentlyHidden ? 'text' : 'password';
      eyeIcon.style.display = isCurrentlyHidden ? 'none' : '';
      eyeOffIcon.style.display = isCurrentlyHidden ? '' : 'none';

      button.setAttribute(
        'aria-label',
        isCurrentlyHidden ? 'Masquer le mot de passe' : 'Afficher le mot de passe',
      );
    });
  });
}
