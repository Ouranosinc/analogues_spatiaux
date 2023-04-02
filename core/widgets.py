# widgets.py
from dask.diagnostics import ProgressBar
from io import StringIO
from panel import Row, Tabs
from panel.viewable import Viewer
from panel.widgets import Progress as _Progress, Toggle
import param

from typing import (ClassVar, List)
class TabsMod(Tabs):
    closablelist = param.List([],item_type=bool)
    _manual_params: ClassVar[List[str]] = ['closablelist'] + Tabs._manual_params
    
    def __init__(self, *objects, **params):
        super().__init__(*objects, **params)
        self.closablelist = [self.closable for i in objects]
        
    def _get_objects(self, model, old_objects, doc, root, comm=None):  
        new_models = super()._get_objects(model, old_objects, doc, root, comm=None)
        for i,panel in enumerate(new_models):
            if i < len(self.closablelist):
                panel.closable = self.closablelist[i]
            else:
                panel.closable = self.closable
                self.closablelist.append( self.closable)
        return new_models
    
    def _manual_update(self, events, model, doc, root, parent, comm):
        for event in events:
            if event.name == 'closablelist':
                for i,child in enumerate(model.tabs):
                    child.closable = event.new[i]
        super()._manual_update(events, model, doc, root, parent, comm)
        

# Task/Dask callback and progress.
class Progress(ProgressBar, Viewer):
    """Object to control a Progress widget from dask."""

    def __init__(self, *args, **kwargs):
        dt = kwargs.pop('delta', 1)
        self.pb = _Progress(*args, **kwargs)
        self.pb.value = -1
        super().__init__(out=StringIO(), dt=dt)

    def _draw_bar(self, frac, elapsed):
        """Change the bar's value"""
        self.pb.value = int(frac * 100)

    def __panel__(self):
        return self.pb

    def __enter__(self):
        self.pb.value = 0
        self.pb.active = True
        self.was_visible = self.pb.visible
        self.pb.visible = True
        return super().__enter__()

    def __exit__(self, *args, **kwargs):
        self.pb.visible = self.was_visible
        self.pb.value = 100
        self.pb.active = False
        return super().__exit__(*args, **kwargs)


class ColoredToggleGroup(Viewer):
    value = param.Integer(default=0)

    def __init__(self, qflags, **params):
        self._buttons = [
            Toggle(
                name=f"#{i}",
                css_classes=[f"tg-{f.lower()}", 'tgx'],
                value=(i == 1),
                width_policy='fixed',
                width=45,
                margin=1
            )
            for i, f in enumerate(qflags, 1)
        ]
        super().__init__(**params)

        for b in self._buttons:
            b.param.watch(self.toggle, 'value')

        self._layout = Row(*self._buttons)

    def __panel__(self):
        return self._layout

    def toggle(self, event):
        if event.obj.value:
            for i, b in enumerate(self._buttons):
                if b is event.obj:
                    self.value = i
                elif b.value:
                    b.value = False
