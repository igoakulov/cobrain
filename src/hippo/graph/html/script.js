var data = JSON.parse(document.getElementById("graph-data").textContent);

var width = window.innerWidth;
var height = window.innerHeight;

var categoryColors = {};
for (var i = 0; i < data.categories.length; i++) {
  var c = data.categories[i];
  categoryColors[c.id] = c.color;
}

var nodes = data.nodes.map(function (d) {
  return Object.assign({}, d);
});
var parentLinks = data.parentLinks.map(function (d) {
  return Object.assign({}, d);
});
var relatedLinks = data.relatedLinks.map(function (d) {
  return Object.assign({}, d);
});

var maxWordCount =
  d3.max(nodes, function (d) {
    return d.word_count;
  }) || 1;
var sizeScale = function (wordCount) {
  return 4 + 12 * (wordCount / maxWordCount);
};

var selectedIds = {};
var isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;

var simulation = d3
  .forceSimulation(nodes)
  .force(
    "parent",
    d3
      .forceLink(parentLinks)
      .id(function (d) {
        return d.id;
      })
      .distance(40)
      .strength(0.8),
  )
  .force(
    "related",
    d3
      .forceLink(relatedLinks)
      .id(function (d) {
        return d.id;
      })
      .distance(40)
      .strength(0.1),
  )
  .force("charge", d3.forceManyBody().strength(-300))
  .force("collide", d3.forceCollide().radius(20))
  .force("x", d3.forceX().strength(0.1))
  .force("y", d3.forceY().strength(0.1));

var svg = d3
  .select("#graph")
  .append("svg")
  .attr("width", width)
  .attr("height", height)
  .on("click", function (event) {
    if (event.target.tagName === "svg") {
      selectedIds = {};
      node
        .selectAll("circle")
        .attr("class", function (d) {
          return getNodeClass(d);
        })
        .style("stroke", "none");
      updateButtons();
    }
  });

var searchTimeout = null;

function searchNodes(query) {
  query = query.toLowerCase().trim();
  if (query.length < 2) {
    node.style("opacity", 1);
    linkParent.style("opacity", 1);
    linkRelated.style("opacity", 1);
    return;
  }
  var useOr = query.indexOf("|") >= 0;
  var useOrWords = !useOr && query.indexOf(" or ") >= 0;
  var terms = (
    useOr ? query.split("|") : query.split(useOrWords ? " or " : " ")
  )
    .map(function (t) {
      return t.trim().toLowerCase();
    })
    .filter(function (t) {
      return t.length > 0;
    });
  var matchedIds = {};
  node.style("opacity", function (d) {
    var match = matchesNode(d, terms, useOr || useOrWords);
    if (match) {
      matchedIds[d.id] = true;
    }
    return match ? 1 : 0.1;
  });
  linkParent.style("opacity", function (d) {
    return matchedIds[d.source.id] && matchedIds[d.target.id] ? 1 : 0.1;
  });
  linkRelated.style("opacity", function (d) {
    return matchedIds[d.source.id] && matchedIds[d.target.id] ? 1 : 0.1;
  });
}

function matchesNode(d, terms, useOr) {
  var fields = [d.id, d.title, d.category]
    .concat(d.aliases || [])
    .concat(d.sources || []);
  var searchStr = fields.join(" ").toLowerCase();
  if (useOr) {
    for (var i = 0; i < terms.length; i++) {
      if (searchStr.indexOf(terms[i]) >= 0) {
        return true;
      }
    }
    return false;
  }
  for (var i = 0; i < terms.length; i++) {
    if (searchStr.indexOf(terms[i]) < 0) {
      return false;
    }
  }
  return true;
}

var zoom = d3
  .zoom()
  .scaleExtent([0.1, 3])
  .on("zoom", function (event) {
    g.attr("transform", event.transform);
  });
svg.call(zoom);

var g = svg.append("g");

var linkParent = g
  .selectAll(".link-parent")
  .data(parentLinks)
  .join("line")
  .attr("class", "link-parent");

var linkRelated = g
  .selectAll(".link-related")
  .data(relatedLinks)
  .join("line")
  .attr("class", "link-related");

var node = g
  .selectAll(".node")
  .data(nodes)
  .join("g")
  .attr("class", "node")
  .call(
    d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended),
  )
  .on("click", nodeClicked)
  .on("mouseenter", showTooltip)
  .on("mouseleave", hideTooltip);

node
  .append("circle")
  .attr("r", function (d) {
    return sizeScale(d.word_count);
  })
  .attr("class", function (d) {
    return getNodeClass(d);
  })
  .attr("fill", function (d) {
    return categoryColors[d.category] || "#888";
  });

node
  .append("text")
  .attr("class", "activity-label")
  .attr("text-anchor", "middle")
  .attr("dy", "0.35em")
  .attr("font-size", "8px")
  .attr("fill", "#fff")
  .attr("pointer-events", "none")
  .text(function (d) {
    return d.activityLabel || "";
  });

node
  .append("text")
  .attr("dx", 14)
  .attr("dy", 4)
  .attr("font-size", "10px")
  .attr("fill", "#666")
  .text(function (d) {
    return d.id;
  });

var tooltip = d3.select("#tooltip");
var tooltipTimer = null;

function getNodeClass(d) {
  var cls = "node-circle";
  if (selectedIds[d.id]) {
    cls += " selected";
  }
  return cls;
}

function showTooltip(event, d) {
  hideTooltip();
  tooltipTimer = setTimeout(function () {
    var html =
      "<span style='color:#bbb'>id: " +
      d.id +
      "<br>title: " +
      d.title +
      "<br>category: " +
      (d.category || "-") +
      "<br>words: " +
      d.word_count +
      "</span>";
    tooltip
      .html(html)
      .style("left", event.pageX + 10 + "px")
      .style("top", event.pageY + 10 + "px")
      .classed("visible", true);
  }, 200);
}

function hideTooltip() {
  if (tooltipTimer) {
    clearTimeout(tooltipTimer);
    tooltipTimer = null;
  }
  tooltip.classed("visible", false);
}

function dragstarted(event) {
  if (!event.active) {
    simulation.alphaTarget(0.3).restart();
  }
  event.subject.fx = event.subject.x;
  event.subject.fy = event.subject.y;
}

function dragged(event) {
  event.subject.fx = event.x;
  event.subject.fy = event.y;
}

function dragended(event) {
  if (!event.active) {
    simulation.alphaTarget(0);
  }
  event.subject.fx = null;
  event.subject.fy = null;
}

function nodeClicked(event, d) {
  if (event.metaKey || event.shiftKey || selectedIds[d.id]) {
    if (selectedIds[d.id]) {
      delete selectedIds[d.id];
    } else {
      selectedIds[d.id] = true;
    }
  } else {
    selectedIds = {};
    selectedIds[d.id] = true;
  }

  node
    .selectAll("circle")
    .attr("class", function (d) {
      return getNodeClass(d);
    })
    .style("stroke", function (d) {
      return selectedIds[d.id] ? "#fff" : "none";
    })
    .style("stroke-width", function (d) {
      return selectedIds[d.id] ? "4px" : "0";
    });

  updateButtons();
}

function updateButtons() {
  var count = Object.keys(selectedIds).length;
  if (count === 1) {
    var selectedId = Object.keys(selectedIds)[0];
    openBtn.attr("data-id", selectedId);
    openBtn
      .classed("hidden", false)
      .html("Open " + selectedId + ".md \u00B7 " + openHint);
    copyBtn
      .classed("hidden", false)
      .html("Copy " + count + " selected \u00B7 " + copyHint);
  } else if (count > 1) {
    openBtn.classed("hidden", true);
    copyBtn
      .classed("hidden", false)
      .html("Copy " + count + " selected \u00B7 " + copyHint);
  } else {
    openBtn.classed("hidden", true);
    copyBtn.classed("hidden", true);
  }
}

function fitToView() {
  var xVals = nodes.map(function (n) {
    return n.x;
  });
  var yVals = nodes.map(function (n) {
    return n.y;
  });
  var minX = Math.min.apply(null, xVals);
  var maxX = Math.max.apply(null, xVals);
  var minY = Math.min.apply(null, yVals);
  var maxY = Math.max.apply(null, yVals);
  var padding = 2;
  var graphWidth = Math.max(maxX - minX, 1) * padding;
  var graphHeight = Math.max(maxY - minY, 1) * padding;
  var minZoom = Math.min(width / graphWidth, height / graphHeight);
  minZoom = Math.min(minZoom, 1.5);
  if (minZoom < 0.1) {
    minZoom = 0.1;
  }
  var centerX = (minX + maxX) / 2;
  var centerY = (minY + maxY) / 2;
  var tx = width / 2 - centerX * minZoom;
  var ty = height / 2 - centerY * minZoom;
  g.attr("transform", "translate(" + tx + "," + ty + ")scale(" + minZoom + ")");
  svg.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(minZoom));
  simulation.alpha(0.3).restart();
  return minZoom;
}

simulation.alpha(1).restart();
for (var i = 0; i < 300; i++) {
  simulation.tick();
}
simulation.stop();

var minZoom = fitToView();

var maxZoom = (Math.min(width, height) * 0.2) / 40;

zoom.scaleExtent([minZoom, maxZoom]);

window.addEventListener("resize", function () {
  width = window.innerWidth;
  height = window.innerHeight;
  svg.attr("width", width).attr("height", height);
});

simulation.on("tick", function () {
  linkParent
    .attr("x1", function (d) {
      return d.source.x;
    })
    .attr("y1", function (d) {
      return d.source.y;
    })
    .attr("x2", function (d) {
      return d.target.x;
    })
    .attr("y2", function (d) {
      return d.target.y;
    });

  linkRelated
    .attr("x1", function (d) {
      return d.source.x;
    })
    .attr("y1", function (d) {
      return d.source.y;
    })
    .attr("x2", function (d) {
      return d.target.x;
    })
    .attr("y2", function (d) {
      return d.target.y;
    });

  node.attr("transform", function (d) {
    return "translate(" + d.x + "," + d.y + ")";
  });
});

var copyBtn = d3.select("#copy-btn");
var openBtn = d3.select("#open-btn");
var searchInput = d3.select("#search");
var copyHint = isMac ? "⌘C" : "Ctrl+C";
var openHint = "↵";

searchInput.attr(
  "placeholder",
  "Search " +
    data.topicCount +
    " topics by title, category, sources...   " +
    (isMac ? "⌘K" : "Ctrl+K"),
);

searchInput.on("input", function () {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(function () {
    searchNodes(searchInput.property("value"));
  }, 200);
});

updateButtons();

window.addEventListener("keydown", function (event) {
  if (event.code === "Space") {
    simulation.alphaTarget(0.7).restart();
    return;
  }
  if (event.code === "Escape") {
    searchInput.property("value", "").node().blur();
    node.style("opacity", 1);
    linkParent.style("opacity", 1);
    linkRelated.style("opacity", 1);
    return;
  }
  if ((event.metaKey || event.ctrlKey) && event.key === "k") {
    event.preventDefault();
    searchInput.node().focus();
    return;
  }
  var count = Object.keys(selectedIds).length;
  if (event.code === "Enter" && count === 1) {
    event.preventDefault();
    openFile();
    return;
  }
  if ((event.metaKey || event.ctrlKey) && event.key === "c" && count > 0) {
    copySelection();
    event.preventDefault();
  }
});

window.addEventListener("keyup", function (event) {
  if (event.code === "Space") {
    simulation.alphaTarget(0);
  }
});

copyBtn.on("click", function () {
  copySelection();
});

openBtn.on("click", function () {
  openFile();
});

function openFile() {
  var id = openBtn.attr("data-id");
  if (!id) {
    return;
  }
  var path = data.vaultPath + "/topics/" + id + ".md";
  var anchor = d3.select("#open-btn").node();
  anchor.href = "file://" + path;
  anchor.target = "_blank";
  anchor.click();
}

function copySelection() {
  var topicMap = {};
  for (var i = 0; i < nodes.length; i++) {
    topicMap[nodes[i].id] = nodes[i];
  }

  var selected = Object.keys(selectedIds).sort();
  var output = [];

  for (var i = 0; i < selected.length; i++) {
    var id = selected[i];
    var topic = topicMap[id];
    var parent = topic.parent;

    if (!parent || !selectedIds[parent]) {
      output.push(id + " - " + topic.title);
      collectChildren(id, topicMap, output, 1);
    }
  }

  var text = output.join("\n");
  var ta = document.createElement("textarea");
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
}

function collectChildren(parentId, topicMap, output, indent) {
  for (var i = 0; i < nodes.length; i++) {
    var n = nodes[i];
    if (n.parent === parentId && selectedIds[n.id]) {
      output.push(makeIndent(indent) + n.id + " - " + n.title);
      collectChildren(n.id, topicMap, output, indent + 1);
    }
  }
}

function makeIndent(level) {
  var s = "";
  for (var i = 0; i < level; i++) {
    s += "  ";
  }
  return s;
}
