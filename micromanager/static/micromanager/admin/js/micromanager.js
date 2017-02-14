function openDialog(msg, title){
	var html = '<div class="modal-header"><button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button><h4 class="modal-title">' + title + '</h4></div><div class="modal-body"><p>' + msg + '</p></div><div class="modal-footer"><button type="button" class="btn btn-primary" data-dismiss="modal">OK</button></div>';

	$("#ModalContent").html(html);
	$("#Modal").modal("show");
}


function cms_add_element(identifier){

	var container = $(identifier);

	// only multi-content fields have a container
	if (container.length){

		var current_num = container.children().length;

		function addElement(){

			var new_elem = container.children("[data-new=1]").first().clone(true, true);

			// images need id adjustment
			var input =	new_elem.find("input");
			if (input.length && input[0].hasAttribute("id")){
				var old_id = input.attr("id");
				var old_id_head = old_id.split("--")[0];
				var next_num = current_num + 1;
				var new_id = old_id_head + "--" + next_num.toString();
				input.attr("id", new_id);

				var label = new_elem.find("label");
				if (label.length > 0){
					label.attr("for", new_id);
				}
			}

			container.append(new_elem);

		}

		var max_num = null;

		if (container[0].hasAttribute("data-max-num")){
			max_num = parseInt(container.attr("data-max-num"));
		}

		if (max_num != null){

			if (max_num == null || current_num < max_num){
				addElement();
			}
			else {
				alert("maximum number reached");
			}

		}
		else {
			addElement();
		}

	}

}


/*
	this is bound to empty image uploads or existing images
	empty images need the localized_page_id
*/
function cms_manage_image(ev, template_content_id, language, on_delete){

	var field = $(ev.target);

	// create a form with category, contenttype and pk[optional]
	var url = field.attr("data-url");

	var formData = new FormData();

	var is_update = field[0].hasAttribute("data-pk");

	formData.append("file", field[0].files[0]);

	if (template_content_id != null){
		formData.append("template_content_id", template_content_id);
	}
	formData.append("language", language);

	if (is_update == true){
		formData.append("pk", field.attr("data-pk"));
	}

	$.ajax(url, {
		type: "POST",
		processData: false,
		contentType: false,
		data: formData,
		success : function(html){
			
			if (is_update == false){
				// it is a new field -> add a new blank field if allowed
				var container_id = "#" + field.attr("data-type") + "-container";
				cms_add_element(container_id);
			}

			// replace the current input with the new one
			var new_field = $(html);
			new_field.find(".delete-filecontent-button").on("click", on_delete);
			field.parent().parent().replaceWith(new_field);
			reloadPreview();
		}
	});

}
