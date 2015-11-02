# pypolinet

Uses the [indico.io](https://indico.io/) political API to analyze the ideological sentiment of a given user's twitter network.

Note: plots generated require a customization of `pandas.tools.plotting.parallel_coordinates`. Specifically, I removed labelling as part of plot generation so I could pass in custom legend creation. This meant replacing `ax.plot(x, y, color=colors[kls], label=label, **kwds)` with `ax.plot(x, y, color=colors[kls], **kwds)` in `parallel_coordinates` and commenting out the legend creation line a few lines down. `matplotlib` will throw a fit about extra values for label if you try to do custom labelling unless you make this change.
