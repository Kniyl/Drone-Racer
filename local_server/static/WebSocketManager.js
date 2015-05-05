var WebSocketManager = function(sElem, hElem, mElem, tElem) {
  var service = this;
  var statusElem = sElem;
  var messageElem = mElem;
  var tableElem = tElem;
  var titleElem = hElem;
  this.interval = null;
  this.timer = 0;
  this.state = 'canceled';

  this.initDOM = function() {
    tableElem.find('tr:gt(0)').remove();
    tableElem.find('th:eq(8)').html('Temps du dernier tour')
    titleElem.html('Aucune course en ce moment');
    messageElem.html('La prochaine course est en train d’être préparée. Patientez sagement.');
    tableElem.hide(100);
  };

  this.getTime = function(time_sec) {
    mins = Math.floor(time_sec / 60);
    if (mins < 10) { mins = '0' + mins; }
    secs = time_sec % 60;
    if (secs < 10) {
      secs = '0' + secs.toFixed(1);
    } else {
      secs = secs.toFixed(1);
    }
    return mins + ':' + secs;
  }

  this.updateStatus = function(message) {
    statusElem.html(message);
    statusElem.parent().show();
  };

  this.cancelHandler = function(data) {
    service.state = 'canceled';
    clearInterval(service.interval);
    service.initDOM();
  };

  this.finishHandler = function(data) {
    if (service.state === 'running') {
      service.state = 'finished';
      clearInterval(service.interval);
      messageElem.html('La course est terminée. Attendez que le juge de course publie le classement définitif.');
    }
  };

  this.setupHandler = function(data) {
    if (service.state === 'canceled') {
      service.initDOM();
      service.state = 'setup';
      titleElem.html(data.course.nom);
      $.each(data.pilotes, function(idx, driver) {
        var row = $('<tr id="Pilote'+driver.id+'">');
        row.append($('<td>').append(driver.id));
        row.append($('<td>').append(driver.nom));
        row.append($('<td>').append(driver.drone));
        row.append($('<td>').append('-'));
        row.append($('<td>').append('0'));
        row.append($('<td>').append('00:00.0'));
        row.append($('<td>').append('0'));
        row.append($('<td>').append('-'));
        row.append($('<td>').append('-'));
        row.append($('<td>').append('-'));
        row.append($('<td>').append('Au sol'));
        tableElem.append(row);
      });
      tableElem.show(1000);
      var msg = 'Portes activées sur ce circuit : ' + data.course.portes.join(' ');
      if (data.course.temps !== null) {
        msg = msg + '<br /> Temps disponible : ' + service.getTime(data.course.temps/10);
      }
      if (data.course.tours !== null) {
        msg = msg + '<br /> ' + data.course.tours + ' tours à réaliser';
      }
      messageElem.html(msg);
    }
  };

  this.warmupHandler = function(data) {
    if (service.state === 'setup') {
      titleElem.html(data.texte);
      if (data.start) {
        service.state = 'running';
        service.timer = 0;
        titleElem.html('00:00.0');
        service.interval = setInterval(function(){
          ++service.timer;
          titleElem.html(service.getTime(service.timer/10));
        }, 100);
      }
    }
  };

  this.updateHandler = function(data) {
    if (service.state !== 'canceled') {
      var row = $('#Pilote'+data.id).find('td');
      row.eq(3).html(data.position);
      row.eq(4).html(data.points);
      row.eq(5).html(service.getTime(data.temps));
      row.eq(6).html(data.tours);
      if (data.retard !== null) { row.eq(7).html(service.getTime(data.retard)); }
      if (data.tour !== null) { row.eq(8).html(service.getTime(data.tour)); }
      row.eq(9).html(data.porte || '-');
      if (data.finish === null) {
        row.eq(10).html('En vol');
      } else {
        row.eq(10).html(data.finish ? 'Arrivé' : 'Déclaré mort');
      }
    }
  };

  this.leaderboardHandler = function(data) {
    if (service.state === 'finished') {
      service.state === 'canceled';
      tableElem.find('th:eq(8)').html('Meilleur tour')
      $.each(data.drones, function(idx, drone) {
        var row = $('#Pilote'+drone.id).find('td');
        row.eq(3).html(drone.position);
        row.eq(4).html(drone.points);
        row.eq(5).html(service.getTime(drone.temps));
        row.eq(6).html(drone.tours);
        if (drone.retard !== null) { row.eq(7).html(service.getTime(drone.retard)); }
        if (drone.tour !== null) { row.eq(8).html(service.getTime(drone.tour)); }
        row.eq(9).html(drone.porte || '-');
        if (drone.finish === null) {
          row.eq(10).html('En vol');
        } else {
          row.eq(10).html(drone.finish ? 'Arrivé' : 'Déclaré mort');
        }
      });
      messageElem.html('La course est terminée, les résultats sont maintenant définitifs.');
    }
  };

  this.processMessage = function(message) {
    var func = service[message.action+'Handler'];
    if (func) {
      func(message);
    } else {
      service.displayMessage(message);
    }
  };

  this.displayMessage = function(message) {
    console.log(message);
  };

  this.initDOM();
};

