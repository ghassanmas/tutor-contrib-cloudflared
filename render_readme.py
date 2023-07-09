"A util script to render README.template.md"


from jinja2 import  Template

from tutorcloudflared import cli


FILENAME = './README.template.md'
OUTPUT = 'README.md'

f = open(FILENAME)
template = Template(f.read())
f.close()
template_output = template.render(cli=cli)

output_file = open(OUTPUT,'w')
output_file.write(template_output)
output_file.close()
