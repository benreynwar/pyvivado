import jinja2
import hashlib
import json

def format_file(template_filename, output_filename, parameters):
    with open(template_filename, 'r') as f:
        template_text = f.read()
        template = jinja2.Template(template_text)
    formatted_text = template.render(**parameters)
    with open(output_filename, 'w') as g:
        g.write(formatted_text)

def files_hash(fns):
  h = hashlib.sha1()
  for fn in fns:
      with open(fn, 'rb') as f:
          finished = False
          while not finished:
              buf = f.read(4096)
              if buf:
                  h.update(hashlib.sha1(buf).digest())
              else: 
                  finished = True
  return h.digest()

