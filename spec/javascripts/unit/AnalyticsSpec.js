describe("GOVUK.Analytics", function () {
  var analytics,
      sortCalls;

  SortCallsToGaByMethod = function (calls) {
    var gaMethodCalls = {},
        callNum = calls.length;

    while (callNum--) {
      var method = calls[callNum].args.shift(),
          args = calls[callNum].args;

      if (gaMethodCalls.hasOwnProperty(method)) {
        gaMethodCalls[method].push(args);
      } else {
        gaMethodCalls[method] = [args];
      }
    }
    this._calls = gaMethodCalls;
  };
  SortCallsToGaByMethod.prototype.callsTo = function (method) {
    if (this._calls.hasOwnProperty(method)) {
      return this._calls[method];
    }
    return [];
  };

  beforeEach(function () {
    window.ga = function() {};
    spyOn(window, 'ga');
  });

  describe('when initialised', function () {

    it('should initialise pageviews, events and virtual pageviews', function () {
      spyOn(window.GOVUK.GDM.analytics, 'register');
      spyOn(window.GOVUK.GDM.analytics.pageViews, 'init');
      spyOn(window.GOVUK.GDM.analytics.events, 'init');

      window.GOVUK.GDM.analytics.init();

      expect(window.GOVUK.GDM.analytics.register).toHaveBeenCalled();
      expect(window.GOVUK.GDM.analytics.pageViews.init).toHaveBeenCalled();
      expect(window.GOVUK.GDM.analytics.events.init).toHaveBeenCalled();
    });
  });

  describe('when registered', function() {
    var universalSetupArguments;

    beforeEach(function() {
      GOVUK.GDM.analytics.init();
      universalSetupArguments = window.ga.calls.allArgs();
    });

    it('configures a universal tracker', function() {
      expect(universalSetupArguments[0]).toEqual(['create', 'UA-49258698-1', {
        'cookieDomain': document.domain
      }]);
    });
  });

  describe("Virtual Page Views", function () {
    var $analyticsString;

    afterEach(function () {
      $analyticsString.remove();
    });

    it("Should not call google analytics without a url", function () {
      $analyticsString = $("<div data-analytics='trackPageView'/>");
      $(document.body).append($analyticsString);
      window.GOVUK.GDM.analytics.virtualPageViews.init();
      expect(window.ga.calls.any()).toEqual(false);
    });

    it("Should call google analytics if url exists", function () {
      $analyticsString = $("<div data-analytics='trackPageView' data-url='http://example.com'/>");
      $(document.body).append($analyticsString);
      window.GOVUK.GDM.analytics.virtualPageViews.init();
      expect(window.ga.calls.first().args).toEqual([ 'send', 'pageview', { page: 'http://example.com/vpv' } ]);
      expect(window.ga.calls.count()).toEqual(1);
    });


    it("Should add '/vpv/' to url before question mark", function () {
      $analyticsString = $('<div data-analytics="trackPageView" data-url="http:/testing.co.uk/testrubbs?sweet"/>');
      $(document.body).append($analyticsString);
      window.GOVUK.GDM.analytics.virtualPageViews.init();
      expect(window.ga.calls.first().args[2]).toEqual({page: "http:/testing.co.uk/testrubbs/vpv?sweet"});
    });

    it("Should add '/vpv/' to url at the end if no question mark", function () {
      $analyticsString = $("<div data-analytics='trackPageView' data-url='http://example.com'/>");
      $(document.body).append($analyticsString);
      window.GOVUK.GDM.analytics.virtualPageViews.init();
      expect(window.ga.calls.first().args[2]).toEqual({page: "http://example.com/vpv"});
    });
  });
});
