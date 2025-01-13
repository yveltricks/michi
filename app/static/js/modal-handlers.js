// File: app/static/js/modal-handlers.js

// Exercise Modal Handling
function initializeExerciseModal() {
    const modal = document.getElementById('exercise-modal');
    const btn = document.getElementById('add-exercise-btn');
    const span = modal.querySelector('.close');
    const searchInput = document.getElementById('exercise-search');
    const exerciseList = document.getElementById('exercise-list');

    // Open modal
    btn.onclick = function() {
        modal.style.display = 'block';
    }

    // Close modal when clicking (X)
    span.onclick = function() {
        modal.style.display = 'none';
    }

    // Handle exercise search
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const exercises = exerciseList.getElementsByClassName('exercise-option');

            Array.from(exercises).forEach(exercise => {
                const name = exercise.getElementsByTagName('h4')[0].textContent.toLowerCase();
                exercise.style.display = name.includes(searchTerm) ? '' : 'none';
            });
        });
    }

    // Handle exercise selection
    if (exerciseList) {
        exerciseList.addEventListener('click', function(e) {
            if (e.target.classList.contains('add-btn')) {
                const exerciseDiv = e.target.closest('.exercise-option');
                const exerciseId = exerciseDiv.dataset.id;
                const exerciseName = exerciseDiv.dataset.name;

                // Add exercise
                addExerciseAndStayOpen(exerciseId, exerciseName);

                // Show feedback
                const addButton = e.target;
                const originalText = addButton.textContent;
                addButton.textContent = 'Added!';
                addButton.style.backgroundColor = '#4CAF50';

                setTimeout(() => {
                    addButton.textContent = 'Add';
                    addButton.style.backgroundColor = '#007bff';
                }, 1000);
            }
        });
    }
}

// Set Type Modal Handling
function initializeSetTypeModal() {
    const setTypeModal = document.getElementById('set-type-modal');
    const closeSetType = setTypeModal.querySelector('.close');

    // Close modal when clicking (X)
    closeSetType.onclick = function() {
        setTypeModal.style.display = 'none';
    }
}

// Handle clicking outside any modal
function handleOutsideClicks(event) {
    const exerciseModal = document.getElementById('exercise-modal');
    const setTypeModal = document.getElementById('set-type-modal');
    
    if (event.target === exerciseModal) {
        exerciseModal.style.display = 'none';
    } else if (event.target === setTypeModal) {
        setTypeModal.style.display = 'none';
    }
}

// Initialize both modals when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeExerciseModal();
    initializeSetTypeModal();
    
    // Add global click handler for outside clicks
    window.addEventListener('click', handleOutsideClicks);
});