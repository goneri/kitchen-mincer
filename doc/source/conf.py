import os
import sys

sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('./'))
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.intersphinx',
              'sphinx.ext.coverage',
              'sphinx.ext.pngmath',
              'sphinx.ext.todo',
              'sphinxcontrib.blockdiag',
              ]
todo_include_todos = True
source_suffix = '.rst'
master_doc = 'index'
project = u'cinder'
copyright = u'2014-present, eNovance SAS'

unused_docs = [
    'api_ext/rst_extension_template',
    'installer',
]
exclude_trees = []
add_module_names = False
show_authors = False
pygments_style = 'sphinx'
modindex_common_prefix = ['kitchen.']
git_cmd = "git log --pretty=format:'%ad, commit %h' --date=local -n1"
html_last_updated_fmt = os.popen(git_cmd).read()
htmlhelp_basename = 'kitchendoc'
latex_documents = [
    ('index', 'Kitchen.tex', u'Kitchen Island Documentation',
     u'Anso Labs, LLC', 'manual'),
]
blockdiag_antialias = True
blockdiag_html_image_format = 'SVG'
