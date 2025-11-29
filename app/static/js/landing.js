/**
 * PlaySync - Landing Page
 */

document.addEventListener('DOMContentLoaded', () => {
    const createRoomBtn = document.getElementById('create-room-btn');
    const joinRoomBtn = document.getElementById('join-room-btn');
    const joinRoomInput = document.getElementById('join-room-input');

    // Initialize Socket
    socketClient.connect();

    // Create Room
    createRoomBtn.addEventListener('click', async () => {
        createRoomBtn.disabled = true;
        createRoomBtn.textContent = 'Creating...';

        try {
            const response = await fetch('/api/create-room', { method: 'POST' });
            const data = await response.json();
            window.location.href = `/room/${data.room_id}`;
        } catch (error) {
            console.error('Failed to create room:', error);
            createRoomBtn.disabled = false;
            createRoomBtn.textContent = 'Create Room';
        }
    });

    // Join Room
    joinRoomBtn.addEventListener('click', () => {
        const roomId = joinRoomInput.value.trim().toUpperCase();
        if (roomId.length === 8) {
            window.location.href = `/room/${roomId}`;
        } else {
            alert('Please enter a valid 8-character room code');
        }
    });

    // Allow Enter key
    joinRoomInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            joinRoomBtn.click();
        }
    });

    // Auto-uppercase input
    joinRoomInput.addEventListener('input', (e) => {
        e.target.value = e.target.value.toUpperCase();
    });
});
