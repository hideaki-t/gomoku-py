from setuptools import setup, Extension
setup(name='gomoku',
      version='0.1',
      description='',
      author='Hideaki Takahashi',
      author_email='mymelo@gmail.com',
      packages=['gomoku', 'gomoku.doublearray'],
      entry_points = {
       'console_scripts': [
         'build_gomoku_dict = gomoku.build:main'
       ]
      },
      #ext_modules=[Extension('gomoku.doublearray._nodealloc', ['gomoku/doublearray/nodealloc.c'], optional=True, extra_compile_args=['-std=c99'])]
      )
