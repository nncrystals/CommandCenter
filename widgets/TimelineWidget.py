"""
Automatically grab the value to be plotted from the service provider.
"""
from collections import OrderedDict
from datetime import datetime

import numpy as np
import pyqtgraph as pg
from Qt import QtWidgets, QtCore
from pyqtgraph import PlotDataItem

from data_class.subject_data import TimelineDataPoint
from services import service_provider
from services.subjects import Subjects
from rx.scheduler.mainloop import QtScheduler

class TimeAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).strftime("%x %X") for value in values]


class TimelineWidget(pg.GraphicsLayoutWidget):
    color_list = ["r", "g", "b", "c", "m", "y", "k", "w"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_height = 300
        self.qt_scheduler = QtScheduler(QtCore)

        self.subjects: Subjects = service_provider.SubjectProvider().get_or_create_instance(None)
        """
        store the dict {
            plot_name: str -> {
                "plot": PlotItem,
                "series": {
                    series-name: str -> PlotDataItem
                }
            }
        }
        """
        self.plots = OrderedDict()

    def configure_subscriptions(self):
        self.subjects.add_to_timeline \
            .subscribe(self.update_plot)

    def update_plot(self, x: TimelineDataPoint):
        if x.plot_name in self.plots:
            # existing plot
            plot_entry = self.plots[x.plot_name]
        else:
            # add a new plot
            item: pg.PlotItem = self.addPlot(name=x.plot_name, title=x.plot_name,
                                             axisItems={"bottom": TimeAxisItem(orientation="bottom")})
            item.addLegend()
            item.setFixedHeight(self.plot_height)

            self.nextRow()
            plot_entry = self.plots[x.plot_name] = {"plot": item}

            # schedule resize later
            def resize_callback(schd, state=0):
                items = list(self.plots.items())[-1]
                plot_obj = items[1]['plot']
                y = plot_obj.sceneBoundingRect().bottomLeft().y()
                self.setMinimumSize(300, y)

            self.qt_scheduler.schedule(resize_callback)

        series: dict
        try:
            series = plot_entry["series"]
        except:
            series = plot_entry["series"] = {}

        if x.series_name in series:
            # previously plotted series, update
            existing_series: PlotDataItem = series[x.series_name]
            current_x, current_y = existing_series.getData()
            current_x = np.append(current_x, x.time)
            current_y = np.append(current_y, x.value)
            existing_series.setData(current_x, current_y)

        else:
            # new series, plot it
            series[x.series_name] = plot_entry["plot"].plot(
                [x.time],
                [x.value],
                name=x.series_name,
                pen=pg.mkPen(color=self.color_list[len(series) % len(self.color_list)])
            )


if __name__ == '__main__':
    import rx
    from rx import operators
    from rx.scheduler.mainloop import QtScheduler
    import traceback as tb

    app = QtWidgets.QApplication([])

    w = QtWidgets.QWidget()
    w.setMinimumSize(500,500)
    sa = QtWidgets.QScrollArea(w)
    w.setLayout(QtWidgets.QVBoxLayout(w))
    w.layout().addWidget(sa)
    timeline_widget = TimelineWidget(sa)

    sa.setWidget(timeline_widget)
    sa.setWidgetResizable(True)
    w.show()

    def configure():
        def error_report(x):
            tb.print_stack()

        sc = QtScheduler(QtCore)
        rx.just(1).pipe(
            operators.delay(1.0, sc),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_1", "series_1").add_new_point(1.2))),
            operators.delay(1.0, sc),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_1", "series_1").add_new_point(-1))),
            operators.delay(1.0, sc),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_2", "series_1").add_new_point(1.2))),
            operators.delay(1.0, sc),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_2", "series_1").add_new_point(-12))),
            operators.delay(1.0, sc),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_3", "series_1").add_new_point(1.2))),
            operators.delay(1.0, sc),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_3", "series_1").add_new_point(-12))),
            operators.delay(1.0, sc),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_3", "series_1").add_new_point(1))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_3", "series_2").add_new_point(3))),
            operators.delay(1.0, sc),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_3", "series_1").add_new_point(-6))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_3", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_4", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_5", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_6", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_7", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_8", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_9", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_10", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_11", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_12", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_13", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_14", "series_2").add_new_point(-5))),
            operators.map(lambda x: timeline_widget.update_plot(TimelineDataPoint("plot_15", "series_2").add_new_point(-5))),
        ).subscribe()

    tmr = QtCore.QTimer()
    tmr.timeout.connect(configure)
    tmr.setSingleShot(True)
    tmr.start(1)
    app.exec()
