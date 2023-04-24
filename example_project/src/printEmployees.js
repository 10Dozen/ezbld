//@wrap:function:MyTinyApp.printEmployees:
// Logger.js

this.log.log('Printing employees');
node = document.getElementById('container')
this.employees.forEach(employee => {
	const content = employee.get();
	const p = document.createElement("p")
	p.appendChild(document.createTextNode(content));
	node.appendChild(p);
});
