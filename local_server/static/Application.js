var Application = function(aHost, aPort, aStatusID, aTitleID, aMessageID, aTableID) {
  var app = this;
  var socketManager,
      socketOpenned = false,
      socket;

  app.onSocketOpen = function(nil) {
    socketOpenned = true;
    socketManager.updateStatus('Communication établie avec succès pour suivre les courses en direct.');
  };

  app.onSocketClose = function(nil) {
    if (socketOpenned) {
      socketManager.updateStatus('Communication terminée. Le direct n’est plus accessible. Rafraîchissez la page pour relancer la connexion.');
    } else {
      socketManager.updateStatus('Impossible de se connecter pour suivre le direct. Soit vous n’ouvrez pas la page depuis l’adresse '+aHost+', soit votre navigateur ne supporte pas websocket.');
    }
    socketOpenned = false;
  };

  app.onSocketError = function(error) {
    socketManager.updateStatus('Une erreur est survenue : '+error.data);
  };

  app.onSocketMessage = function(message) {
    try {
      var data=$.parseJSON(message.data);
      socketManager.processMessage(data);
    } catch(e) {}
  };

  // Constructor
  (function() {
    socketManager = new WebSocketManager(
        $('#'+aStatusID),
        $('#'+aTitleID),
        $('#'+aMessageID),
        $('#'+aTableID)
    );
    socket = new WebSocket('ws://'+aHost+':'+aPort+'/websocket/');
    socket.onopen = app.onSocketOpen;
    socket.onclose = app.onSocketClose;
    socket.onerror = app.onSocketError;
    socket.onmessage = app.onSocketMessage;
    socketManager.updateStatus('Communication possible avec le serveur pour suivre les courses en direct. Attendez la fin de la phase de connexion.');
  })();
};

