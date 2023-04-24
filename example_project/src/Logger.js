//@wrap:function:const Logger:component_name, log_level=2
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
}