// Version: 0.1.0.1
// Build by ezbld tool =)

// Logger defined before use
const Logger = function (component_name, log_level=2) {
    // Logger.js
    
    this.component = component_name
    this.level = log_level
    
    this.error = function (msg) {
    	if (this.level < 2) return
    	console.error(this.component, msg)
    }
    
    this.log = function (msg) {
    	if (this.level < 3) return
    	console.log(this.component, msg)
    }}

// Main programm
const MyTinyApp = new (function () {
    // core.js
    
    this.Constants = {
    	Departments: {}
    };
    this.Entities = {};
    this.employees = [];
    this.log = new Logger('MyTinyApp', 3);
})()

{
    // constants.js
    
    MyTinyApp.Constants.Departments['HR'] = 'Human Resources';
    MyTinyApp.Constants.Departments['ENG'] = 'Engineering';
    MyTinyApp.Constants.Departments['FIN'] = 'Financical';
}

// Entities objects
MyTinyApp.Entities.Employee = function (name, dept, salary) {
    // Entities/employee.js
    
    this.name = name
    this.department = dept
    this.salary = salary
    
    this.get = function() {
    	return `${this.name} (${this.department}, salary: ${this.salary})`
    }
}

// Functions
MyTinyApp.addEmployee = function (name, department, salary) {
    // addEmployee.js
    
    this.log.log(`Adding employee ${name} to ${department} department`);
    this.employees.push(new MyTinyApp.Entities.Employee(name, department, salary))
}

MyTinyApp.printEmployees = function () {
    // Logger.js
    
    this.log.log('Printing employees');
    node = document.getElementById('container')
    this.employees.forEach(employee => {
    	const content = employee.get();
    	const p = document.createElement("p")
    	p.appendChild(document.createTextNode(content));
    	node.appendChild(p);
    });
}

//On document ready
// onDocumentReady.js

document.addEventListener("DOMContentLoaded", function(event) {
	MyTinyApp.addEmployee('John Doe', MyTinyApp.Constants.Departments.ENG, 3000);
	MyTinyApp.addEmployee('Jane Doe', MyTinyApp.Constants.Departments.FIN, 3500);
	MyTinyApp.addEmployee('Alexander Anderson', MyTinyApp.Constants.Departments.HR, 2250);
	MyTinyApp.printEmployees()
});
