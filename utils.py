import jinja2

def format_file(template_filename, output_filename, parameters):
    with open(template_filename, 'r') as f:
        template_text = f.read()
        template = jinja2.Template(template_text)
    formatted_text = template.render(**parameters)
    with open(output_filename, 'w') as g:
        g.write(formatted_text)
