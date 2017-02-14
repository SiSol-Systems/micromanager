CKEDITOR.editorConfig = function( config ) {
	config.toolbarGroups = [
		{ name: 'document', groups: [ 'mode', 'document', 'doctools' ] },
		{ name: 'clipboard', groups: [ 'clipboard', 'undo' ] },
		{ name: 'basicstyles', groups: [ 'basicstyles', 'cleanup' ] },
		{ name: 'editing', groups: [ 'find', 'selection', 'spellchecker', 'editing' ] },
		{ name: 'forms', groups: [ 'forms' ] },
		{ name: 'paragraph', groups: [ 'list', 'indent', 'blocks', 'align', 'bidi', 'paragraph' ] },
		{ name: 'links', groups: [ 'links' ] },
		{ name: 'insert', groups: [ 'insert' ] },
		{ name: 'styles', groups: [ 'styles' ] },
		{ name: 'colors', groups: [ 'colors' ] },
		{ name: 'tools', groups: [ 'tools' ] },
		{ name: 'others', groups: [ 'others' ] },
		{ name: 'about', groups: [ 'about' ] }
	];

	config.removeButtons = 'Templates,Save,Source,NewPage,Preview,Print,Form,HiddenField,Checkbox,Radio,TextField,Textarea,Select,Button,ImageButton,CopyFormatting,CreateDiv,Language,PageBreak,Cut,Undo,Redo,Copy,Paste,PasteText,PasteFromWord,Replace,Find,SelectAll,Scayt,Outdent,Indent,Blockquote,BidiLtr,BidiRtl,Subscript,Superscript,Anchor,Image,Flash,Table,HorizontalRule,Smiley,SpecialChar,Iframe,ShowBlocks,Font,FontSize,Format,Styles';
};
