// to advertise parent iframe that the app has been loaded
window.parent.postMessage("dummy message", "*");   

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById("header").style.display = "none";  
}, false);
