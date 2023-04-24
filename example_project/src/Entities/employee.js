//@wrap:function:MyTinyApp.Entities.Employee:name, dept, salary
// Entities/employee.js

this.name = name
this.department = dept
this.salary = salary

this.get = function() {
	return `${this.name} (${this.department}, salary: ${this.salary})`
}
