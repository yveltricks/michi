/**
 * Common workout handling functions shared between starting a new workout and performing routines
 */
const workoutHandlers = {
    /**
     * Helper function to handle notifications API errors gracefully
     * @returns {Array} Empty notifications array
     */
    handleEmptyNotifications: function() {
        return {
            success: true,
            notifications: [],
            unread_count: 0
        };
    },
    
    /**
     * Calculate recommended values based on previous performance
     * @param {Object} exercise The exercise data
     * @param {Array} previousSets Previous sets data
     * @returns {Object} Recommended values
     */
    calculateRecommendedValues: function(exercise, previousSets) {
        if (!exercise.range_enabled || !previousSets || previousSets.length === 0) {
            return null;
        }
        
        // Get the last few completed sets
        const recentSets = previousSets.filter(set => set.completed).slice(-3);
        if (!recentSets.length) {
            return null;
        }
        
        const result = {
            isRecommended: {}
        };
        
        // Check if all sets were at the upper range
        let allAtUpperRange = true;
        let allAtLowerRange = true;
        
        for (const set of recentSets) {
            if (exercise.input_type.includes('reps')) {
                if (exercise.max_reps && set.reps < exercise.max_reps) {
                    allAtUpperRange = false;
                }
                if (exercise.min_reps && set.reps > exercise.min_reps) {
                    allAtLowerRange = false;
                }
            } else if (exercise.input_type.includes('duration')) {
                if (exercise.max_duration && set.time < exercise.max_duration) {
                    allAtUpperRange = false;
                }
                if (exercise.min_duration && set.time > exercise.min_duration) {
                    allAtLowerRange = false;
                }
            } else if (exercise.input_type.includes('distance')) {
                if (exercise.max_distance && set.distance < exercise.max_distance) {
                    allAtUpperRange = false;
                }
                if (exercise.min_distance && set.distance > exercise.min_distance) {
                    allAtLowerRange = false;
                }
            }
        }
        
        // Handle weight-based exercises
        if (['weight_reps', 'weighted_bodyweight', 'duration_weight', 'weight_distance'].includes(exercise.input_type)) {
            const lastSet = recentSets[recentSets.length - 1];
            
            if (lastSet && lastSet.weight) {
                let weight = parseFloat(lastSet.weight);
                
                if (allAtUpperRange) {
                    // Increase weight by 2.5kg
                    weight += 2.5;
                    result.isRecommended.weight = true;
                } else if (allAtLowerRange) {
                    // Decrease weight by 2.5kg if consistently at lower range
                    weight = Math.max(0, weight - 2.5);
                    result.isRecommended.weight = true;
                }
                
                result.weight = weight;
            }
        }
        
        return result;
    },
    
    /**
     * Save a workout to the server
     * @param {Object} workoutData The workout data object
     * @param {string} title Workout title
     * @param {string} description Workout description/notes
     * @param {number} rating Workout rating
     * @param {number} routineId Optional ID of the routine this workout is based on
     * @param {Object} stats Workout statistics (volume, sets, reps)
     * @param {Function} onSuccess Success callback
     * @param {Function} onError Error callback
     */
    saveWorkout: function(workoutData, title, description, rating, routineId, stats, successCallback, errorCallback) {
        console.log("Preparing to save workout:", {
            exercises: workoutData.exercises ? workoutData.exercises.length : 0,
            title: title,
            description: description,
            rating: rating,
            routineId: routineId,
            stats: stats
        });
        
        // Validation checks
        if (!workoutData || !workoutData.exercises || workoutData.exercises.length === 0) {
            const error = 'No exercises found in workout data';
            console.error(error);
            if (errorCallback) errorCallback(error);
            return false;
        }
        
        const hasCompletedSets = workoutData.exercises.some(exercise => 
            exercise.sets && exercise.sets.some(set => set.completed)
        );
        
        if (!hasCompletedSets) {
            const error = 'Please complete at least one set before finishing your workout.';
            console.error(error);
            if (errorCallback) errorCallback(error);
            return false;
        }
        
        // Clean up exercise data for API
        const cleanedExercises = workoutData.exercises.map(exercise => {
            // Create a clean copy of the exercise
            const cleanExercise = {
                id: exercise.id,
                name: exercise.name,
                input_type: exercise.input_type
            };
            
            // Only include completed sets
            if (exercise.sets) {
                cleanExercise.sets = exercise.sets.filter(set => set.completed).map(set => {
                    // Start with a clean set object
                    const cleanSet = {
                        completed: true,
                        set_type: set.set_type || 'normal'
                    };
                    
                    // Add type-specific fields with proper type conversion
                    if (exercise.input_type === 'weight_reps') {
                        cleanSet.weight = parseFloat(set.weight) || 0;
                        cleanSet.reps = parseInt(set.reps) || 0;
                    } else if (exercise.input_type === 'bodyweight_reps') {
                        cleanSet.reps = parseInt(set.reps) || 0;
                    } else if (exercise.input_type === 'duration') {
                        cleanSet.time = parseInt(set.time) || 0;
                    } else if (exercise.input_type === 'distance_duration') {
                        cleanSet.distance = parseFloat(set.distance) || 0;
                        cleanSet.time = parseInt(set.time) || 0;
                    } else if (exercise.input_type === 'weighted_bodyweight') {
                        cleanSet.additional_weight = parseFloat(set.additional_weight) || 0;
                        cleanSet.reps = parseInt(set.reps) || 0;
                    } else if (exercise.input_type === 'assisted_bodyweight') {
                        cleanSet.assistance_weight = parseFloat(set.assistance_weight) || 0;
                        cleanSet.reps = parseInt(set.reps) || 0;
                    } else if (exercise.input_type === 'duration_weight') {
                        cleanSet.weight = parseFloat(set.weight) || 0;
                        cleanSet.time = parseInt(set.time) || 0;
                        
                        // Special handling for planks to ensure duration is set
                        if (exercise.name && exercise.name.toLowerCase().includes('plank')) {
                            // If time is not set, use defaults or fallback to 60 seconds
                            if (!cleanSet.time) {
                                cleanSet.time = exercise.defaults?.time || 60;
                                console.log(`Setting plank duration to ${cleanSet.time}s from defaults`);
                            }
                            
                            // Store user weight separately if available 
                            const volumeElement = document.getElementById('workout-volume');
                            if (volumeElement && volumeElement.dataset.userWeight) {
                                cleanSet.userWeight = parseFloat(volumeElement.dataset.userWeight);
                                console.log(`Storing user weight for plank: ${cleanSet.userWeight}kg`);
                            }
                        }
                    } else if (exercise.input_type === 'weight_distance') {
                        cleanSet.weight = parseFloat(set.weight) || 0;
                        cleanSet.distance = parseFloat(set.distance) || 0;
                    }
                    
                    return cleanSet;
                });
            }
            
            // Copy any range settings if they exist
            if (exercise.range_enabled !== undefined) {
                cleanExercise.range_enabled = Boolean(exercise.range_enabled);
            }
            
            if (exercise.rest_duration !== undefined) {
                cleanExercise.rest_duration = parseInt(exercise.rest_duration) || 0;
            }
            
            return cleanExercise;
        });
        
        // Calculate final duration using the workout timer and completed exercise durations
        let calculatedDuration = 0;
        if (typeof calculateWorkoutDuration === 'function') {
            calculatedDuration = calculateWorkoutDuration();
        } else {
            // Fallback to timer element
            const timerElement = document.getElementById('workout-timer');
            if (timerElement) {
                const timerText = timerElement.textContent;
                if (timerText) {
                    const parts = timerText.split(':');
                    if (parts.length === 3) {
                        calculatedDuration = parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
                    }
                }
            }
        }
        
        // Get total EXP gained from element if available
        let expGained = 0;
        const expElement = document.getElementById('session-exp');
        if (expElement && expElement.textContent) {
            expGained = parseInt(expElement.textContent) || 0;
        }
        
        // Prepare workout data for API
        const apiData = {
            exercises: cleanedExercises,
            title: title || 'Workout',
            description: description || '', // Ensure we're using description, not notes
            rating: parseInt(rating) || 3,
            duration: calculatedDuration,
            volume: parseFloat(stats?.volume) || 0,
            total_reps: parseInt(stats?.totalReps) || 0,
            sets_completed: parseInt(stats?.totalSets) || 0,
            exp_gained: parseInt(expGained || stats?.sessionExp) || 0,
            started_at: workoutData.started_at || new Date().toISOString()
        };
        
        if (routineId) {
            apiData.routine_id = parseInt(routineId) || 0;
        }
        
        console.log("Saving workout data:", apiData);
        
        // Make API call to save workout
        fetch('/workout/api/log-workout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(apiData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Workout saved successfully:', data);
                
                // Reset workout data after successful save
                this.resetWorkoutData();
                
                if (successCallback) {
                    // Use the redirect_url from the server response if available
                    if (data.redirect_url) {
                        console.log(`Using server-provided redirect URL: ${data.redirect_url}`);
                        // Call success callback with the data
                        successCallback({
                            ...data,
                            session_id: data.session_id || null
                        });
                    } else if (data.session_id) {
                        console.log(`Using session_id for redirect: ${data.session_id}`);
                        // Always redirect to the workout page after routine completion
                        // instead of trying to access the session directly
                        successCallback({
                            ...data,
                            redirect_url: '/workout/workout'
                        });
                    } else {
                        console.log(`No redirect info available, using workout page`);
                        successCallback({
                            ...data,
                            redirect_url: '/workout/workout'
                        });
                    }
                }
            } else {
                console.error('Error saving workout:', data.error);
                if (errorCallback) {
                    errorCallback(data.error || 'Failed to save workout');
                }
            }
        })
        .catch(error => {
            console.error('Error saving workout:', error);
            
            // Ensure we call the error callback with a clear message
            const errorMessage = error.message || 'Network error while saving workout';
            console.error('Detailed error:', errorMessage);
            
            if (errorCallback) {
                try {
                    errorCallback(errorMessage);
                } catch (callbackError) {
                    console.error('Error in error callback:', callbackError);
                    alert('Failed to save workout: ' + errorMessage);
                }
            } else {
                // If no error callback provided, show an alert
                alert('Failed to save workout: ' + errorMessage);
            }
            
            // Try to re-enable the submit button if we can find it
            try {
                const completeButtons = document.querySelectorAll('#complete-workout, .finish-workout-btn');
                completeButtons.forEach(button => {
                    button.disabled = false;
                    button.textContent = 'Complete Workout';
                });
            } catch (e) {
                console.error('Failed to re-enable complete button:', e);
            }
        });
        
        return true;
    },
    
    /**
     * Update exercise stats based on a completed set
     * @param {Object} exercise The exercise object containing input_type
     * @param {Object} set The completed set
     * @param {Object} stats Stats object to update
     */
    updateStats: function(exercise, set, stats) {
        if (!set.completed) return stats;
        
        stats.totalSets++;
        
        if (set.reps) {
            stats.totalReps += parseInt(set.reps);
        }
        
        // Get user weight from data attribute if available
        const volumeElement = document.getElementById('workout-volume');
        const userWeight = volumeElement && volumeElement.dataset.userWeight ? 
            parseFloat(volumeElement.dataset.userWeight) : null;
        
        // Special handling for duration-weight exercises like weighted planks
        if (exercise.input_type === 'duration_weight' && exercise.name && exercise.name.toLowerCase().includes('plank')) {
            console.log(`Processing plank exercise with weight=${set.weight || 0}, time=${set.time || 0}`);
            
            // Make sure we have weight and time values
            if (!set.weight) set.weight = exercise.defaults?.weight || 0;
            if (!set.time) set.time = exercise.defaults?.time || 0;
            
            // Make sure we record weight and time in the set data
            if (set.weight > 0) {
                console.log(`Setting plank weight: ${set.weight}kg`);
            }
            if (set.time > 0) {
                console.log(`Setting plank duration: ${set.time}s`);
            }
            
            // Include user weight in volume calculation if available
            const totalWeight = (userWeight ? userWeight : 0) + parseFloat(set.weight || 0);
            const duration = parseFloat(set.time || 0);
            
            if (totalWeight > 0 && duration > 0) {
                // Calculate volume: total weight * (duration in seconds / 60)
                const setVolume = totalWeight * (duration / 60);
                console.log(`Calculated plank volume: ${setVolume} (${totalWeight}kg × ${duration}s ÷ 60)`);
                stats.volume = (stats.volume || 0) + setVolume;
            }
        } else {
            // Calculate volume using our volume calculation function
            const setVolume = this.calculateVolume(exercise, set, userWeight);
            if (setVolume > 0) {
                stats.volume = (stats.volume || 0) + setVolume;
            }
        }
        
        return stats;
    },
    
    /**
     * Calculate EXP gained from a set
     * @param {Object} set The completed set
     * @returns {number} EXP gained
     */
    calculateSetExp: function(set) {
        if (!set.completed) return 0;
        
        if (set.weight && set.reps) {
            return Math.ceil(set.weight * set.reps / 10);
        } else if (set.reps) {
            return Math.ceil(set.reps / 2);
        } else if (set.duration) {
            return Math.ceil(set.duration / 10);
        }
        
        return 0;
    },
    
    /**
     * Calculate volume based on exercise type and set data
     * @param {Object} exercise The exercise data including input_type
     * @param {Object} set The set data
     * @param {number} userWeight Optional user weight for bodyweight exercises
     * @returns {number} The calculated volume
     */
    calculateVolume: function(exercise, set, userWeight) {
        if (!set || !set.completed) return 0;
        
        const inputType = exercise.input_type;
        
        if (inputType === 'bodyweight_reps') {
            if (!userWeight) {
                // Try to fetch user weight from data attribute if available
                const weightElement = document.querySelector('[data-user-weight]');
                if (weightElement) {
                    userWeight = parseFloat(weightElement.dataset.userWeight);
                }
            }
            if (!userWeight) return 0; // Can't calculate without weight
            return userWeight * (set.reps || 0);
            
        } else if (inputType === 'weighted_bodyweight') {
            if (!userWeight) {
                const weightElement = document.querySelector('[data-user-weight]');
                if (weightElement) {
                    userWeight = parseFloat(weightElement.dataset.userWeight);
                }
            }
            if (!userWeight) return 0;
            return (userWeight + (set.additional_weight || 0)) * (set.reps || 0);
            
        } else if (inputType === 'assisted_bodyweight') {
            if (!userWeight) {
                const weightElement = document.querySelector('[data-user-weight]');
                if (weightElement) {
                    userWeight = parseFloat(weightElement.dataset.userWeight);
                }
            }
            if (!userWeight) return 0;
            return (userWeight - (set.assistance_weight || 0)) * (set.reps || 0);
            
        } else if (inputType === 'weight_reps') {
            return (set.weight || 0) * (set.reps || 0);
            
        } else if (inputType === 'weight_distance') {
            return (set.weight || 0) * (set.distance || 0);
        }
        
        return 0;
    },
    
    /**
     * Reset workout data after completion
     * Call this after a workout is successfully saved
     */
    resetWorkoutData: function() {
        console.log('Resetting workout data');
        
        // Check if window.workoutData exists before resetting
        if (window.workoutData) {
            window.workoutData = {
                exercises: [],
                title: '',
                description: '',
                rating: 3,
                started_at: new Date().toISOString()
            };
        }
        
        // Clear any stats counters
        const statsElements = [
            'sets-done', 
            'reps-done', 
            'workout-volume', 
            'session-exp'
        ];
        
        statsElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.textContent = '0';
        });
        
        // Re-render the exercise list if the function exists
        if (typeof renderExercises === 'function') {
            renderExercises();
        }
        
        return true;
    }
}; 