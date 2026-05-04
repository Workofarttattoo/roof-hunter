# TODO: Refactor long functions identified in code quality analysis
#!/usr/bin/env python3
"""
QuLab Patent Search and Analysis Module
=========================================

Integrates USPTO patent search capabilities into QuLab's digital twin framework.
Enables comprehensive intellectual property analysis for innovation assessment.

Features:
- USPTO API integration for patent searching
- Patent landscape analysis
- Innovation gap identification
- Digital twin patent evaluation
- Competitive intelligence gathering

Author: QuLab Infinite - Patent Intelligence Integration
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re
import logging
from collections import Counter, defaultdict


@dataclass
class Patent:
    """USPTO patent data structure"""

    patent_number: str
    title: str
    abstract: str = ""
    inventors: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)
    filing_date: Optional[str] = None
    grant_date: Optional[str] = None
    classifications: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    description: str = ""

    # Analysis fields
    relevance_score: float = 0.0
    technology_area: str = ""
    innovation_level: str = ""
    competitive_impact: str = ""


@dataclass
class PatentSearchResult:
    """Results from patent search"""

    query: str
    total_results: int
    patents: List[Patent]
    search_time: float
    api_calls: int
    timestamp: str


@dataclass
class PatentLandscapeAnalysis:
    """Comprehensive patent landscape analysis"""

    technology_area: str
    time_period: Tuple[str, str]  # (start_date, end_date)
    total_patents: int
    key_players: Dict[str, int]  # assignee -> patent count
    technology_trends: Dict[str, int]  # technology -> patent count
    innovation_gaps: List[str]
    competitive_threats: List[str]
    opportunity_areas: List[str]
    patent_quality_metrics: Dict[str, float]


class QuLabPatentSearch:
    """
    USPTO patent search and analysis integration for QuLab.

    Provides comprehensive patent intelligence capabilities for:
    - Innovation assessment
    - Competitive analysis
    - Technology gap identification
    - Intellectual property strategy
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize patent search system

        Args:
            api_key: USPTO API key (optional, increases rate limits)
        """
        self.api_key = api_key
        self.base_url = "https://developer.uspto.gov/api/patent/search"
        self.session = requests.Session()

        # Rate limiting
        self.requests_per_hour = 100 if api_key else 10
        self.request_times = []

        # Analysis tools
        self.nlp_processor = self._initialize_nlp_processor()

        logging.info("Initialized QuLab Patent Search system")

    def _initialize_nlp_processor(self):
        """Initialize natural language processing for patent analysis"""
        # Simple keyword-based processor (could be enhanced with ML models)
        return {
            'technology_keywords': {
                'digital_twin': ['digital twin', 'virtual twin', 'simulation model', 'predictive model'],
                'quantum_computing': ['quantum computer', 'quantum processor', 'qubit', 'superconducting'],
                'materials_science': ['material', 'alloy', 'composite', 'nanostructure', 'crystal'],
                'biotechnology': ['biotech', 'genetic', 'protein', 'cell culture', 'drug delivery'],
                'ai_ml': ['machine learning', 'artificial intelligence', 'neural network', 'deep learning'],
                'robotics': ['robot', 'automation', 'control system', 'sensor network'],
                'energy': ['battery', 'fuel cell', 'solar', 'wind', 'energy storage']
            },
            'innovation_indicators': [
                'novel', 'improved', 'enhanced', 'optimized', 'breakthrough',
                'revolutionary', 'innovative', 'advanced', 'cutting-edge'
            ]
        }

    def search_patents(self, query: str, rows: int = 100, start: int = 0,
                      date_range: Optional[Tuple[str, str]] = None) -> PatentSearchResult:
        """
        Search USPTO patents

        Args:
            query: Search query
            rows: Number of results to return (max 100)
            start: Starting result index
            date_range: (start_date, end_date) in YYYYMMDD format

        Returns:
            PatentSearchResult with search results
        """

        start_time = time.time()

        # Build search parameters
        params = {
            "q": query,
            "fl": "patentNumber,title,abstract,inventorName,assigneeName,filingDate,grantDate,classifications,references,claims",
            "rows": min(rows, 100),
            "start": start
        }

        # Add date filtering if specified
        if date_range:
            start_date, end_date = date_range
            params["fq"] = f"filingDate:[{start_date} TO {end_date}]"

        # Rate limiting
        self._enforce_rate_limit()

        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()
            patents = self._parse_patent_results(data)

            result = PatentSearchResult(
                query=query,
                total_results=data.get('total', 0),
                patents=patents,
                search_time=time.time() - start_time,
                api_calls=1,
                timestamp=datetime.now().isoformat()
            )

            self.request_times.append(time.time())
            return result

        except Exception as e:
            logging.error(f"Patent search failed: {e}")
            return PatentSearchResult(
                query=query,
                total_results=0,
                patents=[],
                search_time=time.time() - start_time,
                api_calls=1,
                timestamp=datetime.now().isoformat()
            )

    def _parse_patent_results(self, data: Dict[str, Any]) -> List[Patent]:
        """Parse USPTO API response into Patent objects"""

        patents = []

        if 'results' not in data:
            return patents

        for result in data['results']:
            try:
                patent = Patent(
                    patent_number=result.get('patentNumber', ''),
                    title=result.get('title', ''),
                    abstract=result.get('abstract', ''),
                    inventors=result.get('inventorName', []) if isinstance(result.get('inventorName'), list) else [result.get('inventorName', '')],
                    assignees=result.get('assigneeName', []) if isinstance(result.get('assigneeName'), list) else [result.get('assigneeName', '')],
                    filing_date=result.get('filingDate'),
                    grant_date=result.get('grantDate'),
                    classifications=result.get('classifications', []) if isinstance(result.get('classifications'), list) else [result.get('classifications', '')],
                    references=result.get('references', []) if isinstance(result.get('references'), list) else [result.get('references', '')],
                    claims=result.get('claims', []) if isinstance(result.get('claims'), list) else [result.get('claims', '')]
                )

                # Perform initial analysis
                patent.relevance_score = self._calculate_relevance_score(patent)
                patent.technology_area = self._classify_technology_area(patent)
                patent.innovation_level = self._assess_innovation_level(patent)

                patents.append(patent)

            except Exception as e:
                logging.warning(f"Failed to parse patent: {e}")
                continue

        return patents

    def _calculate_relevance_score(self, patent: Patent) -> float:
        """Calculate relevance score for patent based on content analysis"""

        score = 0.0
        text = f"{patent.title} {patent.abstract}".lower()

        # Technology relevance
        tech_keywords = sum(1 for category in self.nlp_processor['technology_keywords'].values()
                          for keyword in category if keyword.lower() in text)
        score += tech_keywords * 0.3

        # Innovation indicators
        innovation_count = sum(1 for indicator in self.nlp_processor['innovation_indicators']
                              if indicator in text)
        score += innovation_count * 0.4

        # Abstract quality (length and specificity)
        if len(patent.abstract) > 200:
            score += 0.3

        # Has claims (indicates serious patent)
        if patent.claims:
            score += 0.2

        return min(score, 1.0)

    def _classify_technology_area(self, patent: Patent) -> str:
        """Classify patent into technology area"""

        text = f"{patent.title} {patent.abstract}".lower()

        for area, keywords in self.nlp_processor['technology_keywords'].items():
            if any(keyword.lower() in text for keyword in keywords):
                return area

        return "general"

    def _assess_innovation_level(self, patent: Patent) -> str:
        """Assess innovation level of patent"""

        text = f"{patent.title} {patent.abstract}".lower()
        innovation_score = 0

        # Count innovation indicators
        for indicator in self.nlp_processor['innovation_indicators']:
            if indicator in text:
                innovation_score += 1

        # Length and detail
        if len(patent.abstract) > 300:
            innovation_score += 1
        if len(patent.claims) > 5:
            innovation_score += 1

        if innovation_score >= 4:
            return "high"
        elif innovation_score >= 2:
            return "medium"
        else:
            return "low"

    def _enforce_rate_limit(self):
        """Enforce API rate limiting"""

        now = time.time()
        window_start = now - 3600  # 1 hour window

        # Remove old requests
        self.request_times = [t for t in self.request_times if t > window_start]

        if len(self.request_times) >= self.requests_per_hour:
            sleep_time = 3600 - (now - self.request_times[0])
            if sleep_time > 0:
                logging.info(f"Rate limit reached, sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)

    def analyze_patent_landscape(self, technology_area: str,
                               years_back: int = 5) -> PatentLandscapeAnalysis:
        """
        Perform comprehensive patent landscape analysis

        Args:
            technology_area: Technology area to analyze
            years_back: Number of years to look back

        Returns:
            Comprehensive patent landscape analysis
        """

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years_back*365)
        date_range = (start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"))

        # Build comprehensive query
        keywords = self.nlp_processor['technology_keywords'].get(technology_area, [])
        if not keywords:
            keywords = [technology_area]

        query = " OR ".join(f'"{keyword}"' for keyword in keywords[:5])  # Limit to top 5 keywords

        # Search patents
        search_result = self.search_patents(query, rows=1000, date_range=date_range)

        # Analyze results
        key_players = self._analyze_key_players(search_result.patents)
        technology_trends = self._analyze_technology_trends(search_result.patents)
        innovation_gaps = self._identify_innovation_gaps(search_result.patents, technology_area)
        competitive_threats = self._analyze_competitive_threats(search_result.patents)
        opportunity_areas = self._identify_opportunity_areas(search_result.patents, technology_area)
        quality_metrics = self._calculate_quality_metrics(search_result.patents)

        return PatentLandscapeAnalysis(
            technology_area=technology_area,
            time_period=date_range,
            total_patents=len(search_result.patents),
            key_players=key_players,
            technology_trends=technology_trends,
            innovation_gaps=innovation_gaps,
            competitive_threats=competitive_threats,
            opportunity_areas=opportunity_areas,
            patent_quality_metrics=quality_metrics
        )

    def _analyze_key_players(self, patents: List[Patent]) -> Dict[str, int]:
        """Analyze key players (assignees) in patent landscape"""

        assignees = []
        for patent in patents:
            assignees.extend(patent.assignees)

        # Count and filter out empty/none values
        assignee_counts = Counter(a for a in assignees if a and a.strip())
        return dict(assignee_counts.most_common(10))

    def _analyze_technology_trends(self, patents: List[Patent]) -> Dict[str, int]:
        """Analyze technology trends in patents"""

        trends = defaultdict(int)

        for patent in patents:
            text = f"{patent.title} {patent.abstract}".lower()

            # Count technology keywords
            for tech_area, keywords in self.nlp_processor['technology_keywords'].items():
                if any(keyword.lower() in text for keyword in keywords):
                    trends[tech_area] += 1

        return dict(trends)

    def _identify_innovation_gaps(self, patents: List[Patent], technology_area: str) -> List[str]:
        """Identify innovation gaps in the patent landscape"""

        gaps = []

        # Check for missing fundamental capabilities
        has_quantum = any('quantum' in (p.title + p.abstract).lower() for p in patents)
        has_ai = any('ai' in (p.title + p.abstract).lower() or 'machine learning' in (p.title + p.abstract).lower() for p in patents)
        has_iot = any('iot' in (p.title + p.abstract).lower() or 'internet of things' in (p.title + p.abstract).lower() for p in patents)

        if technology_area == 'digital_twin' and not has_quantum:
            gaps.append("Limited quantum computing integration in digital twin patents")
        if not has_ai:
            gaps.append("Underutilization of AI/ML in patent filings")
        if not has_iot:
            gaps.append("Missing IoT connectivity in technology patents")

        # Check for recent activity
        recent_patents = [p for p in patents if p.filing_date and
                         datetime.strptime(p.filing_date, "%Y%m%d") > datetime.now() - timedelta(days=365)]

        if len(recent_patents) < len(patents) * 0.3:
            gaps.append("Declining patent activity in recent years")

        return gaps

    def _analyze_competitive_threats(self, patents: List[Patent]) -> List[str]:
        """Analyze competitive threats from patent landscape"""

        threats = []

        # Check for dominant players
        key_players = self._analyze_key_players(patents)
        if key_players:
            top_player, top_count = list(key_players.items())[0]
            total_patents = sum(key_players.values())
            if top_count / total_patents > 0.3:
                threats.append(f"Dominant player {top_player} controls {top_count/total_patents:.1%} of patents")

        # Check for high-quality patents
        high_quality = [p for p in patents if p.relevance_score > 0.7 and len(p.claims) > 10]
        if len(high_quality) > len(patents) * 0.2:
            threats.append("High concentration of high-quality, defensible patents")

        return threats

    def _identify_opportunity_areas(self, patents: List[Patent], technology_area: str) -> List[str]:
        """Identify opportunity areas with low patent density"""

        opportunities = []

        # Find underrepresented technologies
        trends = self._analyze_technology_trends(patents)
        total_patents = len(patents)

        for tech, count in trends.items():
            if count / total_patents < 0.1:  # Less than 10% of patents
                opportunities.append(f"Underexplored area: {tech.replace('_', ' ')} integration")

        # Check for emerging combinations
        if technology_area == 'digital_twin':
            opportunities.extend([
                "AI-driven predictive maintenance integration",
                "Quantum-enhanced simulation accuracy",
                "Multi-physics coupling optimization",
                "Real-time adaptive digital twins"
            ])

        return opportunities

    def _calculate_quality_metrics(self, patents: List[Patent]) -> Dict[str, float]:
        """Calculate patent quality metrics"""

        if not patents:
            return {}

        avg_relevance = sum(p.relevance_score for p in patents) / len(patents)
        avg_claims = sum(len(p.claims) for p in patents) / len(patents)
        high_innovation = sum(1 for p in patents if p.innovation_level == 'high') / len(patents)
        recent_activity = sum(1 for p in patents if p.filing_date and
                             datetime.strptime(p.filing_date, "%Y%m%d") > datetime.now() - timedelta(days=365)) / len(patents)

        return {
            'average_relevance_score': avg_relevance,
            'average_claims_per_patent': avg_claims,
            'high_innovation_ratio': high_innovation,
            'recent_activity_ratio': recent_activity
        }

    def evaluate_technology_readiness(self, technology: str) -> Dict[str, Any]:
        """
        Evaluate technology readiness level based on patent landscape

        Args:
            technology: Technology to evaluate

        Returns:
            Technology readiness assessment
        """

        # Search for technology patents
        search_result = self.search_patents(technology, rows=500)

        if not search_result.patents:
            return {
                'trl_level': 1,
                'assessment': 'Basic principles observed',
                'confidence': 0.9
            }

        # Analyze patent maturity indicators
        patents = search_result.patents

        # TRL 2-3: Basic research
        basic_research = sum(1 for p in patents if 'theory' in (p.title + p.abstract).lower() or
                           'fundamental' in (p.title + p.abstract).lower())

        # TRL 4-5: Technology development
        tech_development = sum(1 for p in patents if 'prototype' in (p.title + p.abstract).lower() or
                             'experimental' in (p.title + p.abstract).lower())

        # TRL 6-7: System integration
        system_integration = sum(1 for p in patents if 'system' in (p.title + p.abstract).lower() or
                               'integration' in (p.title + p.abstract).lower())

        # TRL 8-9: Production ready
        production_ready = sum(1 for p in patents if 'commercial' in (p.title + p.abstract).lower() or
                              'production' in (p.title + p.abstract).lower())

        # Determine TRL level
        total_indicators = basic_research + tech_development + system_integration + production_ready

        if production_ready > total_indicators * 0.4:
            trl = 8
            assessment = "Production ready technology"
        elif system_integration > total_indicators * 0.3:
            trl = 6
            assessment = "System integration demonstrated"
        elif tech_development > total_indicators * 0.3:
            trl = 4
            assessment = "Technology development underway"
        elif basic_research > 0:
            trl = 2
            assessment = "Basic research completed"
        else:
            trl = 1
            assessment = "Basic principles observed"

        return {
            'trl_level': trl,
            'assessment': assessment,
            'patent_count': len(patents),
            'maturity_indicators': {
                'basic_research': basic_research,
                'technology_development': tech_development,
                'system_integration': system_integration,
                'production_ready': production_ready
            },
            'confidence': min(0.9, len(patents) / 100)  # Higher confidence with more patents
        }


def integrate_patent_intelligence_into_digital_twin():
    """
    Demonstrate integration of patent intelligence into digital twin evaluation.

    This shows how patent search can enhance QuLab's digital twin assessments.
    """

    logging.info("🔍 QuLab Patent Intelligence Integration")
    logging.info("=" * 50)

    patent_search = QuLabPatentSearch()

    # Example: Analyze digital twin technology landscape
    logging.info("Analyzing digital twin patent landscape...")
    landscape = patent_search.analyze_patent_landscape("digital_twin", years_back=3)

    logging.info(f"📊 Found {landscape.total_patents} patents in digital twin space")
    logging.info(f"🗓️ Time period: {landscape.time_period[0]} to {landscape.time_period[1]}")

    logging.info("\n🏢 Key Players:")
    for player, count in list(landscape.key_players.items())[:5]:
        logging.info(f"   {player}: {count} patents")

    logging.info("\n📈 Technology Trends:")
    for tech, count in list(landscape.technology_trends.items())[:5]:
        logging.info(f"   {tech}: {count} patents")

    logging.info("\n🎯 Innovation Gaps:")
    for gap in landscape.innovation_gaps[:3]:
        logging.info(f"   • {gap}")

    logging.info("\n⚠️ Competitive Threats:")
    for threat in landscape.competitive_threats[:3]:
        logging.info(f"   • {threat}")

    logging.info("\n💡 Opportunity Areas:")
    for opportunity in landscape.opportunity_areas[:3]:
        logging.info(f"   • {opportunity}")

    # Technology readiness assessment
    logging.info("\n🏭 Technology Readiness Assessment:")
    trl_assessment = patent_search.evaluate_technology_readiness("digital twin simulation")
    logging.info(f"   TRL Level: {trl_assessment['trl_level']}")
    logging.info(f"   Assessment: {trl_assessment['assessment']}")
    logging.info(f"   Confidence: {trl_assessment['confidence']:.1f}")

    return {
        'landscape_analysis': landscape,
        'trl_assessment': trl_assessment,
        'patent_count': landscape.total_patents
    }


def main():
    """Main demonstration of patent search integration"""

    logging.info("🤖 QuLab Patent Search & Digital Twin Integration")
    logging.info("=" * 60)

    # Example patent search
    patent_search = QuLabPatentSearch()

    logging.info("Searching for patents on 'financial modeling predictive digital twin simulation'...")

    search_result = patent_search.search_patents(
        "financial modeling predictive digital twin simulation",
        rows=10
    )

    logging.info(f"Found {search_result.total_results} total patents, showing first {len(search_result.patents)}:")

    for i, patent in enumerate(search_result.patents[:5], 1):
        logging.info(f"\n{i}. Patent {patent.patent_number}")
        logging.info(f"   Title: {patent.title}")
        logging.info(f"   Technology Area: {patent.technology_area}")
        logging.info(f"   Innovation Level: {patent.innovation_level}")
        logging.info(f"   Relevance Score: {patent.relevance_score:.2f}")
        if patent.abstract:
            logging.info(f"   Abstract: {patent.abstract[:200]}...")

    # Integration demonstration
    logging.info("\n🔗 Integrating with Digital Twin Evaluation...")
    results = integrate_patent_intelligence_into_digital_twin()

    logging.info("\n✅ Patent Intelligence Integration Complete")
    logging.info(f"Enhanced digital twin evaluation with {results['patent_count']} patents analyzed")
    logging.info("Patent landscape analysis now available for all QuLab digital twin assessments")


if __name__ == "__main__":
    main()