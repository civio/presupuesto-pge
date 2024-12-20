function RegionComparisonMap(budget_data_URL, population_data_URL, geo_data_URL) {
  var path = d3.geoPath(),
      projection = d3.geoMercator();

  var ccaaLabels = ["Todas","Andalucía", "Aragón", "Asturias", "Illes Balears",
        "Canarias","Cantabria","Castilla y León","Castilla La Mancha","Cataluña","Comunitat Valenciana",
        "Extremadura","Galicia","Madrid","Murcia","Navarra","País Vasco","La Rioja","Ceuta","Melilla"];

  var availableYears = [2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
      balanceByYearAndByRegion,
      balanceByYearByType,
      balanceByYearByRegionByType,
      populationByRegionByYear = {};

  var MODE_PER_PERSON = "PER PERSON",
      MODE_TOTAL = "TOTAL";

  var currentMode,
      currentYear,
      currentYearData = null,
      prevItemRegion = null,
      regOverColor = null,
      _selectedPolicyID = null,
      _clickedPolicy = null,
      regSelected = null,
      _selectedRegion = null,
      _overRegion = null;


  // Entrada principal a la ejecución del script
  this.start = function(uiState) {
    showVis(false);
    currentMode = uiState.format;
    currentYear = uiState.year;

    this.loadPopulation();
  };

  this.update = function() {
    this.updateBarChart();
    updateColors();
    if (_selectedRegion != null || regSelected != null) {
      var a = regSelected;
      _selectedRegion != null && (a = _selectedRegion.properties.ID);
      showRegionInfo(a);
    } else {
      showCountryInfo();
    }
    this.updateNavigationBar();
  };

  function showVis(flag) {
    d3.select("#main").style("visibility", flag == true ? "visible" : "hidden");
  }


  /** CARGA DE DATOS **/
  // Carga los datos de los presupuestos
  function formatBudgetData(a) {
    return {
      ID: a[0].region_id,
      policy_id: a[0].policy_id,
      policy_label: a[0].policy_label,
      amount: getTotalAmount(a)
    }
  }
  this.loadBudgetData = function() {
    var self = this;
    d3.csv(budget_data_URL, function(csv) {
      balanceByYearAndByRegion = d3.nest()
                                    .key(function(d) { return d.year; })
                                    .key(function(d) { return d.region_id; })
                                    .rollup(function(d) { return formatBudgetData(d); })
                                    .object(csv);
      balanceByYearByType = d3.nest()
                              .key(function(d) { return d.year; })
                              .key(function(d) { return d.policy_id; })
                              .rollup(function(d) { return formatBudgetData(d); })
                              .object(csv);
      balanceByYearByRegionByType = d3.nest()
                                      .key(function(d) { return d.year; })
                                      .key(function(d) { return d.region_id; })
                                      .key(function(d) { return d.policy_id; })
                                      .rollup(function(d) { return formatBudgetData(d); })
                                      .object(csv);
      calculateDataPerPerson();

      self.loadMap();
    });
  };

  // Carga los datos de población
  function formatCensoData(a) {
    return {
      ID: a[0].region_id,
      label: a[0].region_name,
      population: getTotal(a)
    }
  }
  this.loadPopulation = function() {
    var self = this;
    d3.csv(population_data_URL, function(csv) {
      populationByRegionByYear = d3.nest()
                                    .key(function(d) { return d.year; })
                                    .key(function(d) { return d.region_id; })
                                    .rollup(function(d) { return formatCensoData(d); })
                                    .object(csv);

      self.loadBudgetData();
    });
  };

  // Carga los datos del mapa (GeoJson)
  this.loadMap = function() {
    var self = this;

    path.projection(projection);

    self.svg = d3.select("#vis #map")
      .append("svg:svg")
      .attr("id", "svg")
      .style('overflow', 'visible')

    self.svg.append("svg:g")
      .attr("id", "states");

    d3.json(geo_data_URL, function(_geoData) {

      d3.select("#states")
        .selectAll("path")
        .data(_geoData.features)
      .enter()
        .append("svg:path")
        .attr("class",   function(d){ return "region_" + d.properties.ID; })
        .on("mouseover", function(d){ return self.mouseOverMap(d); })
        .on("mouseout",  function(d){ return self.mouseOutMap(d); })
        .on("click",     function(d){ return self.clickMap(d); });

      //d3.selectAll("#states path").attr("d", function(a) { return path_proj(a); });

      self.update();
      showVis(true);

      resize();
      d3.select(window).on('resize', resize);
    })
  };

  function resize() {
    var width = $('#map').width();

    projection
      .translate([.742*width, 2.9*width])
      .scale(3.4*width);

    d3.select("#svg")
      .attr("width", width)
      .attr("height", 0.73*width)

    d3.select("#states")
      .selectAll("path")
      .attr("d", path);
  }

  /**  CONTROLES **/
  this.selectTotalAmount = function() {
    this.changeCurrentMode(MODE_TOTAL);
  };

  this.selectPerPerson = function() {
    this.changeCurrentMode(MODE_PER_PERSON);
  };

  this.changeCurrentMode = function(mode) {
    currentMode = mode;
    this.update();
  };


  /** FUNCIONES DEL NAVBAR **/
  this.updateNavigationBar = function() {
    var a = availableYears.length;
        b = d3.entries(availableYears);
        c = d3.select("#yearnavbar");
    var self = this;
    d = 0;

    c.text("");
    b.forEach(function(b) {
      if (currentYear == b.value)
        c.append("span")
         .attr("class", "yearselect")
         .style("float", "left")
         .text(b.value);
      else {
        var e = "yearsel_" + b.value;
        c.append("div")
         .attr("id", e)
         .style("float", "left")
         .append("a")
         .attr("href", "javascript:changeYear(" + b.value + ")")
         .text(b.value)
         .on("mouseover", function() {return self.changeYear(this.innerHTML)});
      }
      ++d != a && c.append("span")
             .style("float", "left")
             .style("margin-left", "5px")
             .style("margin-right", "5px")
             .text(" | ");
    })
  };

  this.changeYear = function(year) {
    if (currentYear != year) {
      currentYear = year;
      this.update();
    }
  };


  /**  MAPA **/
  this.mouseOverMap = function(region) {
    if ( _selectedRegion == null ) {
      _overRegion = region;
      regSelected = _overRegion.properties.ID;
      var selected = d3.select('.region_'+regSelected)
        .style('stroke-width', '1.5px')
        .style('stroke', '#111');
      // move over region on top
      this.svg.selectAll("path").sort(function (a, b){ return (a.properties.ID != regSelected) ? -1 : 1; })
      this.update();
    }
  };

  this.mouseOutMap = function(region) {
    if ( _selectedRegion == null ) {
      d3.select('.region_'+regSelected)
        .style('stroke-width', '')
        .style('stroke', '');
      regSelected = null;
      _overRegion = null;
      this.update();
    }
  };

  this.clickMap = function(region) {
    _overRegion = null;
    if ( _selectedRegion != null && _selectedRegion.properties.ID == region.properties.ID ) {
      _selectedRegion = null;
      this.mouseOutMap();
    } else {
      _selectedRegion = null;
      this.mouseOutMap();
      _selectedRegion = region;
      regSelected = _selectedRegion.properties.ID;
      d3.select('.region_'+regSelected)
        .style('stroke-width', '1.5px')
        .style('stroke', '#111');
      // move over region on top
      this.svg.selectAll("path").sort(function (a, b){ return (a.properties.ID != regSelected) ? -1 : 1; })
      this.update();
    }
  };

  function updateColors() {
    var maxmin = getMaxAndMinValues(true);

    getRegionColor = function(region, min, max) {
      var region_id = parseInt(region.properties.ID);
      if (currentYearData === undefined ) return 0;
      if (currentYearData[region_id] != null) {
          _selectedPolicyID != null && currentYearData[region_id][_selectedPolicyID] == null && (currentYearData[region_id][_selectedPolicyID] = [], currentYearData[region_id][_selectedPolicyID][maxmin.prop] = 0, min = 0);
          var k = _selectedPolicyID == null ? currentYearData[region_id][maxmin.prop] : currentYearData[region_id][_selectedPolicyID][maxmin.prop];
      }
      var interp = d3.interpolateRgb(d3.rgb(254, 217, 118), d3.rgb(227, 26, 28));
      return interp((k - min) / (max - min));
    };

    var states = d3.selectAll("#states path");
    if (_overRegion != null || prevItemRegion || _selectedRegion) {
        var region_id = _selectedRegion == null ?
                    prevItemRegion == null ? _overRegion.properties.ID : prevItemRegion :
                    _selectedRegion.properties.ID;
        states = d3.select("#states path.region_" + region_id)
    }
    _overRegion != null && _selectedRegion == null && (regOverColor = getRegionColor(_overRegion, maxmin.curMin, maxmin.curMax));
    _selectedRegion != null && (regOverColor = getRegionColor(_selectedRegion, maxmin.curMin, maxmin.curMax));

    states.transition(300).style("fill", function(region, d) {
      return getRegionColor(region, maxmin.curMin, maxmin.curMax)
    });
    prevItemRegion = (prevItemRegion != null ? null : region_id);
  }

  /** BARCHART **/
  this.updateBarChart = function() {
    var a = regSelected;
    var b = regSelected == null ? balanceByYearByType[currentYear] : balanceByYearByRegionByType[currentYear][a];
    var c = d3.entries(b);
    var f = [];
    f.data = [];
    f.byYear = [];
    var g = [];
    g.data = [];
    g.byYear = [];
    var h = d3.entries(regSelected == null ? balanceByYearByType : balanceByYearByRegionByType);
    h.forEach(function(b) {
      if (b.key >= availableYears[0] && b.key <= availableYears[availableYears.length - 1]) {
        var c = d3.entries(regSelected == null ? b.value : b.value[a]);
        var d = d3.max(c, function(a) {return a.value.amount});
        var e = d3.min(c, function(a) {return a.value.amount});
        f.data.push(d);
        f.byYear[b.key] = f.data.length - 1;
        g.data.push(e);
        g.byYear[b.key] = g.data.length - 1
      }
    });

    var i = d3.max(f.data, function(a) {return a});
    j = d3.min(g.data, function(a) {return a});
    m = c.sort(function(a, b) {
      if (a.value.policy_label == null || b.value.policy_label == null) return 0;
      var c = a.value.policy_label.toLowerCase(),
          d = b.value.policy_label.toLowerCase();
      if (c < d) return -1;
      if (c > d) return 1;
      return 0
    });

    var n = d3.selectAll("#functionsKey")
              .selectAll("div.functionalArea")
              .data(m);

    var o = n.enter().append("div");
    var self = this;
    o.attr("id", function(a, b) {return "barchart_" + a.value.policy_id + "_text"})
      .attr("class", "functionalArea")
      .on("mouseover", function(a, b) {return self.mouseOverBarChart(a, b, true)})
      .on("mouseout", function(a, b) {return self.mouseOutBarChart(a, b)})
      .on("click", function(a, b) {return self.clickBarChart(a, b)});
    o.append("div")
      .attr("id", function(a, b) {return "funcchart_" + a.value.policy_id})
      .attr("class", "bar");
    o.append("div")
      .attr("class", "functional_label");

    d3.selectAll("#functionsKey div.functional_label")
      .data(m)
      .style("font-weight", function(a) {return a.value.policy_id == _selectedPolicyID ? "600" : "400"})
      .style("color", function(a) {return a.value.policy_id == _selectedPolicyID ? "#111" : "#666"})
      .text(function(a) {return a.value.policy_label != null ? a.value.policy_label : ""});

    d3.selectAll("#functionsKey div.bar")
      .data(m)
      .style("background-color", function(a) {return a.value.policy_id == _selectedPolicyID ? "#111" : "#cccccc"})
      .transition(300)
      .call(function(a) {
        var b = function(a) {return Math.max(1, (a.value.amount - j) / i * 100)};
        a.style("width", function(a) {return b(a) + "px"});
        a.style("left", function(a) {return -5 - b(a) + "px"})
      });

    n.exit().remove();
  };

  this.mouseOverBarChart = function(a, b, c) {
    _clickedPolicy == null && this.selectPolicy(a.value.policy_id)
  };

  this.mouseOutBarChart = function(a, b) {
    _clickedPolicy == null && this.selectPolicy(null)
  };

  this.clickBarChart = function(a, b) {
    _clickedPolicy == a.value.policy_id ? _clickedPolicy = null : _clickedPolicy = a.value.policy_id, this.selectPolicy(_clickedPolicy)
  };

  this.selectPolicy = function(a) {
    _selectedPolicyID = a;
    this.update();
  };


  /** FUNCIONES DEL INFOBOX **/
  function showCountryInfo() {
    if (_selectedRegion == null) {
      d3.select("#infoTitle").text("Comunidades Autónomas");

      var value = formatValueShort(currentMode == MODE_PER_PERSON ? calculateAverage() : getTotalCountryAmount());
      d3.select("#infoValue")
        .html(value);

      d3.select("#infoAvgBox")
        .style("display", "none");

      d3.select("#infoBar")
        .style("background-color", "");

      updateInfoDesc();
    }
  }

  function showRegionInfo(region) {
    if (currentYearData[region] != null) {
      var value = _selectedPolicyID == null ? currentYearData[region] : currentYearData[region][_selectedPolicyID];
      var maxmin = getMaxAndMinValues(false);
      var max = maxmin.curMax;
      var min = maxmin.curMin;
      var area = maxmin.prop;

      d3.select("#infoTitle")
        .text(ccaaLabels[region]);
      d3.select("#infoValue")
        .html(formatValueShort(value[area]));

      d3.select("#infoAvgBox")
        .style("display", currentMode == MODE_PER_PERSON ? "block" : "none");

      if ( currentMode == MODE_PER_PERSON ) {
        var nationalAverageScale = d3.scaleLinear()
                                    .domain([0, calculateAverage()])
                                    .rangeRound([-100, 0]);
        var deviation = nationalAverageScale(value[area]);
        d3.select("#infoBar")
          .transition(500)
          .style("width", 190 * Math.min(deviation+100, 200) / 200 + "px");
        d3.select("#infoAvgText")
          .text((deviation > 0 ? "+" + deviation : deviation) + "% sobre media país");
      } else {
        d3.select("#infoAvgText").text("");
      }

      updateInfoDesc();
    }

    d3.select("#infobox")
      .style("display", "block")

    d3.select("#infoBar")
      .style("background-color", regOverColor)
  }

  // Dependiendo de modo de visualización actual, modifica la etiqueta del infoBox
  function updateInfoDesc() {
    d3.select("#infoDesc").text(currentMode == MODE_PER_PERSON ? "presupuesto por persona" : "presupuesto total")
  }


  /** CALCULO **/
  function getPopulationByYearByRegion(year, region) {
    return populationByRegionByYear[year][region].population;
  }

  // Suma los presupuestos de una determinada agrupación
  function getTotalAmount(items) {
    var total = 0.0;
    items.forEach(function(item) {
      total += parseFloat(item.total);
    });
    return total;
  }

  // Suma los valores de la población de cada región y devuelve el total
  function getTotal(items) {
    var total = 0;
    items.forEach(function(item) {
      total += parseInt(item.total);
    });
    return total;
  }

  function calculateAverage() {
    if ( currentMode == MODE_TOTAL )  // Makes no sense to average total amounts
      return null;

    var population = 0;
    d3.entries( populationByRegionByYear[currentYear] ).forEach(function(region_id) {
      population += region_id.value.population || 0;
    });
    return getTotalCountryAmount() / population;
  }

  function getTotalCountryAmount() {
    var total = 0;
    d3.entries(currentYearData).forEach(function(region_id) {
      total += _selectedPolicyID ?
                  region_id.value[_selectedPolicyID].amount || 0 :
                  region_id.value.amount || 0
    });
    return total;
  }

  function getMaxAndMinValues(useAbsoluteValues) {
    var data = _selectedPolicyID == null ? balanceByYearAndByRegion : balanceByYearByRegionByType;
    currentYearData = data[currentYear];
    var propName = (currentMode == MODE_PER_PERSON) ? "valuePerPerson" : "amount";
    var max, min;
    var getValue = function(a) {
      return _selectedPolicyID == null ?
                a.value[propName] :
                a.value[_selectedPolicyID] ? a.value[_selectedPolicyID][propName] : 0;
    };

    if ( useAbsoluteValues ) {
      var max_tmp = [];
      var min_tmp = [];
      d3.entries(data).forEach(function(item) {
        if (item.key >= availableYears[0] && item.key <= availableYears[availableYears.length - 1]) {
          var b = d3.entries(item.value);
          max_tmp.push( d3.max(b, getValue) );
          min_tmp.push( d3.min(b, getValue) );
        }
      });
      max = d3.max(max_tmp, function(a) {return a});
      min = d3.max(min_tmp, function(a) {return a});  // XXXX: max????

    } else {
      var d = d3.entries(currentYearData);
      max = d3.max(d, getValue);
      min = d3.min(d, getValue);
    }

    return {
      curMax: max,
      curMin: min,
      prop: propName
    }
  }

  // Cálculo para YR y YRT por persona teniendo en cuenta presupuesto total y población asociada
  function calculateDataPerPerson() {
    d3.entries(balanceByYearAndByRegion).forEach(function(year) {
      if (year.key >= availableYears[0] && year.key <= availableYears[availableYears.length - 1]) {
        d3.entries(year.value).forEach(function(region) {
          balanceByYearAndByRegion[year.key][region.key].valuePerPerson = region.value.amount / getPopulationByYearByRegion(year.key, region.key)
        })
      }
    });

    d3.entries(balanceByYearByRegionByType).forEach(function(year) {
      if (year.key >= availableYears[0] && year.key <= availableYears[availableYears.length - 1]) {
        d3.entries(year.value).forEach(function(region) {
          d3.entries(region.value).forEach(function(type) {
            balanceByYearByRegionByType[year.key][region.key][type.key].valuePerPerson = type.value.amount / getPopulationByYearByRegion(year.key, region.key)
          })
        })
      }
    })
  }


  /** FORMATEO DE SALIDA **/
  function formatValueShort(a) {
    var b = 1e3,
        c = 1e6,
        d = 1e9,
        e = "\u20ac",
        i = "",
        f = "0";
    if (a >= c) i = " M", a = a / c;
    else {
        var g = a.toString().substring(0, h);
        a > b ? i = "" : a = Math.round(100 * a) / 100
    }
    var g = a.toString(),
        h = a.toString().indexOf(".");
    h > -1 && (g = a.toString().substring(0, h));
    f = g.substring(0, g.length - 3) + "." + g.substring(g.length - 3, g.length);
    a < b && (f = g + "," + a.toString().substring(h + 1, h + 3));
    return f + e + i;
  }
};
