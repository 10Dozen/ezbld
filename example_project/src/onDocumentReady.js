// onDocumentReady.js

document.addEventListener("DOMContentLoaded", function(event) {
	MyTinyApp.addEmployee('John Doe', MyTinyApp.Constants.Departments.ENG, 3000);
	MyTinyApp.addEmployee('Jane Doe', MyTinyApp.Constants.Departments.FIN, 3500);
	MyTinyApp.addEmployee('Alexander Anderson', MyTinyApp.Constants.Departments.HR, 2250);
	MyTinyApp.printEmployees()
});