var data = JSON.parse(document.getElementById("graph-data").textContent);

var width = window.innerWidth;
var height = window.innerHeight;
var categoryColors = {};
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
var matchedIds = {};
var searchFocused = false;
var isMac = navigator.userAgent.includes("Mac");
var dateValues = ["⏱", "1D", "1W", "1M", "3M"];
var dateFilterIndex = 0;
var copyHint = isMac ? "⌘C" : "Ctrl+C";
var openHint = "⏎";
var cursorX = window.innerWidth / 2;
var cursorY = window.innerHeight / 2;

for (var i = 0; i < data.categories.length; i++) {
  categoryColors[data.categories[i].id] = data.categories[i].color;
}

function matchesNode(d, terms, useOr) {
  var fields = [d.id, d.title, d.category]
    .concat(d.aliases || [])
    .concat(d.sources || []);
  var searchStr = fields.join(" ").toLowerCase();
  if (useOr) {
    for (var i = 0; i < terms.length; i++) {
      if (searchStr.indexOf(terms[i]) >= 0) return true;
    }
    return false;
  }
  for (var i = 0; i < terms.length; i++) {
    if (searchStr.indexOf(terms[i]) < 0) return false;
  }
  return true;
}

function getNodeClass(d) {
  return selectedIds[d.id] ? "node-circle selected" : "node-circle";
}

function makeIndent(level) {
  var s = "";
  for (var i = 0; i < level; i++) s += "  ";
  return s;
}

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
        .attr("class", getNodeClass)
        .style("stroke", "none")
        .style("stroke-width", "0");
      cursorX = window.innerWidth / 2;
      cursorY = window.innerHeight / 2;
      updateSelection();
    }
  });

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
  .attr("class", getNodeClass)
  .attr("fill", function (d) {
    return categoryColors[d.category] || "#888";
  });

node
  .append("text")
  .attr("text-anchor", "start")
  .attr("dx", function (d) {
    return sizeScale(d.word_count) + 4;
  })
  .attr("dy", "0.35em")
  .attr("font-size", "10px")
  .attr("fill", "#666")
  .text(function (d) {
    return d.id;
  });

var tooltip = d3.select("#tooltip");
var tooltipTimer = null;
var searchTimeout = null;
var selectionStatus = d3.select("#selection-status");
var searchInput = d3.select("#search");
var dateFilter = d3.select("#date-filter");

function showTooltip(event, d) {
  hideTooltip();
  tooltipTimer = setTimeout(function () {
    tooltip
      .html(
        "<span style='color:#bbb'>title: " +
          d.title +
          "<br>category: " +
          (d.category || "-") +
          "<br>words: " +
          d.word_count +
          "</span>",
      )
      .style("left", event.pageX + 10 + "px")
      .style("top", event.pageY + 15 + "px")
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
  if (!event.active) simulation.alphaTarget(0.3).restart();
  event.subject.fx = event.subject.x;
  event.subject.fy = event.subject.y;
}

function dragged(event) {
  event.subject.fx = event.x;
  event.subject.fy = event.y;
}

function dragended(event) {
  if (!event.active) simulation.alphaTarget(0);
  event.subject.fx = null;
  event.subject.fy = null;
}

function nodeClicked(event, d) {
  if (!matchedIds[d.id]) return;
  if (event.metaKey || event.shiftKey || selectedIds[d.id]) {
    selectedIds[d.id] ? delete selectedIds[d.id] : (selectedIds[d.id] = true);
  } else {
    selectedIds = {};
    selectedIds[d.id] = true;
  }
  node
    .selectAll("circle")
    .attr("class", getNodeClass)
    .style("stroke", function (d) {
      return selectedIds[d.id] ? "#fff" : "none";
    })
    .style("stroke-width", function (d) {
      return selectedIds[d.id] ? "4px" : "0";
    });
  updateSelection();
}

function updateSelection() {
  var count = Object.keys(selectedIds).length;
  if (count >= 1) {
    var content =
      count === 1
        ? Object.keys(selectedIds)[0] +
          ".md <span class=key>" +
          copyHint +
          "</span> <span class=key>" +
          openHint +
          "</span>"
        : count + " selected <span class=key>" + copyHint + "</span>";
    selectionStatus
      .classed("visible", true)
      .style("left", cursorX + 20 + "px")
      .style("top", cursorY - 8 + "px")
      .html(content);
  } else {
    selectionStatus.classed("visible", false);
  }
}

function applyFilters(query) {
  var terms =
    query.length >= 2
      ? query
          .toLowerCase()
          .split(" ")
          .filter(function (t) {
            return t.length > 0;
          })
      : [];
  var useOr = query.indexOf("|") >= 0;
  if (useOr)
    terms = query
      .split("|")
      .map(function (t) {
        return t.trim();
      })
      .filter(function (t) {
        return t.length > 0;
      });
  var dateDays = [0, 1, 7, 30, 90][dateFilterIndex];
  var now = new Date();
  matchedIds = {};
  node.style("opacity", function (d) {
    var matchesSearch = terms.length === 0 || matchesNode(d, terms, useOr);
    var matchesDate =
      dateFilterIndex === 0 ||
      (now - new Date(d.updated_at)) / (1000 * 60 * 60 * 24) <= dateDays;
    if (matchesSearch && matchesDate) matchedIds[d.id] = true;
    return matchesSearch && matchesDate ? 1 : 0.1;
  });
  linkParent.style("opacity", function (d) {
    return matchedIds[d.source.id] && matchedIds[d.target.id] ? 1 : 0.1;
  });
  linkRelated.style("opacity", function (d) {
    return matchedIds[d.source.id] && matchedIds[d.target.id] ? 1 : 0.1;
  });
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
  var minZoom = Math.min(
    Math.min(width / graphWidth, height / graphHeight),
    1.5,
  );
  if (minZoom < 0.1) minZoom = 0.1;
  var centerX = (minX + maxX) / 2;
  var centerY = (minY + maxY) / 2;
  var tx = width / 2 - centerX * minZoom;
  var ty = height / 2 - centerY * minZoom;
  g.attr("transform", "translate(" + tx + "," + ty + ")scale(" + minZoom + ")");
  svg.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(minZoom));
  simulation.alpha(0.3).restart();
  return minZoom;
}

function openFile() {
  var id = Object.keys(selectedIds)[0];
  if (!id) return;
  window.open(data.vaultPath + "/topics/" + id + ".md", "_blank");
}

function copySelection() {
  var topicMap = {};
  for (var i = 0; i < nodes.length; i++) topicMap[nodes[i].id] = nodes[i];
  var selected = Object.keys(selectedIds).sort();
  var output = [];
  for (var i = 0; i < selected.length; i++) {
    var topic = topicMap[selected[i]];
    if (!topic.parent || !selectedIds[topic.parent]) {
      output.push(selected[i]);
      collectChildren(selected[i], topicMap, output, 1);
    }
  }
  var text = output.join("\n");
  navigator.clipboard.writeText(text);
  var savedLeft = selectionStatus.style("left");
  var savedTop = selectionStatus.style("top");
  selectionStatus.classed("visible", true).html("Copied!");
  setTimeout(function () {
    updateSelection();
    selectionStatus.style("left", savedLeft).style("top", savedTop);
  }, 1000);
}

function collectChildren(parentId, topicMap, output, indent) {
  for (var i = 0; i < nodes.length; i++) {
    var n = nodes[i];
    if (n.parent === parentId && selectedIds[n.id]) {
      output.push(makeIndent(indent) + n.id);
      collectChildren(n.id, topicMap, output, indent + 1);
    }
  }
}

simulation.alpha(1).restart();
for (var i = 0; i < 300; i++) simulation.tick();
simulation.stop();

var minZoom = fitToView();
zoom.scaleExtent([minZoom, (Math.min(width, height) * 0.2) / 40]);

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

dateFilter.style("font-size", "20px");
searchInput.attr(
  "placeholder",
  (isMac ? "⌘K" : "Ctrl+K") +
    "  Search " +
    data.topicCount +
    " topics by title, category, sources...",
);

document.addEventListener("mousemove", function (event) {
  cursorX = event.pageX;
  cursorY = event.pageY;
  if (selectionStatus.style("display") !== "none") {
    selectionStatus
      .style("left", cursorX + 20 + "px")
      .style("top", cursorY - 8 + "px");
  }
});

searchInput.on("input", function () {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(function () {
    applyFilters(searchInput.property("value"));
  }, 200);
});

searchInput.on("focus", function () {
  searchFocused = true;
  searchInput.attr("placeholder", "Tip: use OR or | for any match...");
  dateFilter.style("color", "#333");
});
searchInput.on("blur", function () {
  searchFocused = false;
  searchInput.attr(
    "placeholder",
    (isMac ? "⌘K" : "Ctrl+K") +
      "  Search " +
      data.topicCount +
      " topics by title, category, sources...",
  );
  dateFilter.style("color", dateFilterIndex === 0 ? "" : "#e0e0e0");
});

dateFilter.on("click", function () {
  dateFilterIndex = (dateFilterIndex + 1) % dateValues.length;
  dateFilter
    .text(dateValues[dateFilterIndex])
    .style("font-size", dateFilterIndex === 0 ? "20px" : "14px")
    .style("transform", dateFilterIndex === 0 ? "" : "none");
  if (searchFocused) {
    dateFilter.style("color", "#333");
  } else {
    dateFilter.style("color", dateFilterIndex === 0 ? "" : "#e0e0e0");
  }
  applyFilters(searchInput.property("value").toLowerCase().trim());
});

window.addEventListener("keydown", function (event) {
  var searchFocused = document.activeElement === searchInput.node();

  if (event.code === "Space" && !searchFocused) {
    simulation.alphaTarget(0.7).restart();
    return;
  }
  if (event.code === "Escape") {
    if (searchFocused) {
      searchInput.property("value", "").node().blur();
      applyFilters("");
    } else if (Object.keys(selectedIds).length > 0) {
      selectedIds = {};
      node
        .selectAll("circle")
        .attr("class", getNodeClass)
        .style("stroke", "none")
        .style("stroke-width", "0");
      updateSelection();
    }
    return;
  }
  if ((event.metaKey || event.ctrlKey) && event.key === "a") {
    if (searchFocused) return; // let browser select text
    event.preventDefault();
    for (var i = 0; i < nodes.length; i++) {
      if (matchedIds[nodes[i].id]) selectedIds[nodes[i].id] = true;
    }
    node
      .selectAll("circle")
      .attr("class", getNodeClass)
      .style("stroke", function (d) {
        return selectedIds[d.id] ? "#fff" : "none";
      })
      .style("stroke-width", function (d) {
        return selectedIds[d.id] ? "4px" : "0";
      });
    updateSelection();
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
  if (event.code === "Space" && document.activeElement !== searchInput.node()) {
    simulation.alphaTarget(0);
  }
});

updateSelection();
applyFilters("");
