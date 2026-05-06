var socket = io();

// JOIN ROOM
function joinRoom(name, room) {
    socket.emit("join_room", {
        name: name,
        room: room
    });
}

// SEND SCORE
function sendScore(name, room, score) {
    socket.emit("answer_result", {
        name: name,
        room: room,
        score: score
    });
}

// NEXT QUESTION (HOST)
function nextQuestion(room) {
    socket.emit("next_question", {
        room: room
    });
}

// LIVE UPDATES
socket.on("leaderboard", function(data) {
    console.log("Leaderboard:", data);
});