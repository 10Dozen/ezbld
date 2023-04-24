//@wrap:function:MyTinyApp.addEmployee:name, department, salary
// addEmployee.js

this.log.log(`Adding employee ${name} to ${department} department`);
this.employees.push(new MyTinyApp.Entities.Employee(name, department, salary))
