from django.forms.widgets import FileInput, Widget, TextInput, Textarea
from django.forms.utils import flatatt
from django.template import loader, Context
from django.utils.encoding import (
    force_str, force_text, python_2_unicode_compatible,
)

from django.utils.html import conditional_escape, format_html, html_safe
from django.utils.safestring import mark_safe


"""
   A widget displaying multiple TextInputs
   - still needs custom RENDER method
   REWRITE THIS - use MultiWidget as blueprint
"""
class MultiContentWidget(Widget):

    template_name = "micromanager/widgets/multi_content_input.html"

    def __init__(self, attrs={}):
        max_ = attrs.get("maxnum", None)

        number = 1

        if max_ and max_ < number:
            number = max_

        widget = attrs.pop("widget", Textarea)
        self.widgets = [widget() for i in range(0,number)]
        super(MultiContentWidget, self).__init__(attrs)
        
    @property
    def is_hidden(self):
        return all(w.is_hidden for w in self.widgets)

    def render(self, name, value, attrs=None):
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []

        # multi content fields may not have an id
        # the user can add fields via javascript
        id_ = attrs.pop("id")

        
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id')
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append(widget.render(name, widget_value, final_attrs))

        widgets_html = mark_safe(self.format_output(output))

        return widgets_html


    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_

    def value_from_datadict(self, data, files, name):
        data = data.getlist(name,[])
        return data

    def value_omitted_from_data(self, data, files, name):
        return all(
            widget.value_omitted_from_data(data, files, name)
            for i, widget in enumerate(self.widgets)
        )

    def format_output(self, rendered_widgets):
        """
        Given a list of rendered widgets (as strings), returns a Unicode string
        representing the HTML for the whole lot.

        This hook allows you to format the HTML design of the widgets, if
        needed.
        """
        
        return ''.join(rendered_widgets)

    def decompress(self, value):
        if value:
            return value
        return []

    def _get_media(self):
        "Media for a multiwidget is the combination of all media of the subwidgets"
        media = Media()
        for w in self.widgets:
            media = media + w.media
        return media
    media = property(_get_media)

    def __deepcopy__(self, memo):
        obj = super(MultiWidget, self).__deepcopy__(memo)
        obj.widgets = copy.deepcopy(self.widgets)
        return obj

    @property
    def needs_multipart_form(self):
        return any(w.needs_multipart_form for w in self.widgets)
