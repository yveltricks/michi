// File: app/static/js/modal-handlers.js

// Exercise Modal Handling
function initializeExerciseModal() {
    const modal = document.getElementById('exercise-modal');
    const btn = document.getElementById('add-exercise-btn');
    const span = modal.querySelector('.close');
    const searchInput = document.getElementById('exercise-search');
    const exerciseList = document.getElementById('exercise-list');

    // Open modal
    if (btn) {
        btn.onclick = function() {
            modal.style.display = 'block';
        }
    }

    // Close modal when clicking (X)
    if (span) {
        span.onclick = function() {
            modal.style.display = 'none';
        }
    }

    // Handle exercise search
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const exercises = exerciseList.getElementsByClassName('exercise-option');

            Array.from(exercises).forEach(exercise => {
                const name = exercise.querySelector('h4').textContent.toLowerCase();
                exercise.style.display = name.includes(searchTerm) ? '' : 'none';
            });
        });
    }

    // Handle exercise selection - Direct click handler
    if (exerciseList) {
        // Add click event listener to each add button directly
        document.querySelectorAll('.exercise-option .add-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const exerciseDiv = this.closest('.exercise-option');
                const exerciseId = exerciseDiv.dataset.id;
                const exerciseName = exerciseDiv.dataset.name;
                
                console.log(`Clicked to add exercise: ${exerciseId} - ${exerciseName}`);
                
                // Call the add exercise function
                if (typeof addExerciseAndStayOpen === 'function') {
                    addExerciseAndStayOpen(exerciseId, exerciseName);
                    
                    // Show feedback
                    const addButton = this;
                    const originalText = addButton.textContent;
                    addButton.textContent = 'Added!';
                    addButton.style.backgroundColor = '#4CAF50';
                    
                    setTimeout(() => {
                        addButton.textContent = originalText;
                        addButton.style.backgroundColor = '#007bff';
                    }, 1000);
                } else {
                    console.error('addExerciseAndStayOpen function not found');
                }
            });
        });
    }
}

// Set Type Modal Handling
function initializeSetTypeModal() {
    const setTypeModal = document.getElementById('set-type-modal');
    const closeSetType = setTypeModal.querySelector('.close');

    // Close modal when clicking (X)
    if (closeSetType) {
        closeSetType.onclick = function() {
            setTypeModal.style.display = 'none';
        }
    }
    
    // Add event delegation for set type options
    const setTypeList = document.getElementById('set-type-list');
    if (setTypeList) {
        setTypeList.addEventListener('click', function(e) {
            if (e.target.classList.contains('select-btn') || e.target.closest('.select-btn')) {
                const typeOption = e.target.closest('.set-type-option');
                const setType = typeOption.dataset.type;
                
                console.log('Set type clicked:', setType);
                
                // Find currentSetTypeSelection in the global scope
                if (window.currentSetTypeSelection && 
                    typeof updateSetType === 'function') {
                    console.log('Updating set type:', 
                              window.currentSetTypeSelection.exerciseIndex, 
                              window.currentSetTypeSelection.setIndex, 
                              setType);
                    
                    updateSetType(
                        window.currentSetTypeSelection.exerciseIndex, 
                        window.currentSetTypeSelection.setIndex, 
                        setType
                    );
                    setTypeModal.style.display = 'none';
                } else {
                    console.error('Could not update set type. Missing selection data or function:', 
                                window.currentSetTypeSelection, typeof updateSetType);
                }
            }
        });
    }
}

// Handle clicking outside any modal
function handleOutsideClicks(event) {
    const modals = document.querySelectorAll('.modal');
    
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Initialize both modals when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing modals from modal-handlers.js');
    initializeExerciseModal();
    initializeSetTypeModal();
    
    // Initialize other modals
    const rangeModal = document.getElementById('range-settings-modal');
    if (rangeModal) {
        const closeRangeModal = rangeModal.querySelector('.close');
        if (closeRangeModal) {
            closeRangeModal.onclick = function() {
                rangeModal.style.display = 'none';
            }
        }
    }
    
    const restModal = document.getElementById('rest-timer-modal');
    if (restModal) {
        const closeRestModal = restModal.querySelector('.close');
        if (closeRestModal) {
            closeRestModal.onclick = function() {
                restModal.style.display = 'none';
            }
        }
    }
    
    // Add global click handler for outside clicks
    window.addEventListener('click', handleOutsideClicks);
});