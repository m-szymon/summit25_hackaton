import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { NgIf, NgFor, DecimalPipe } from '@angular/common';

interface WikipediaArticle {
  index: number;
  title: string;
  text: string;
  alternator: boolean;
}

@Component({
  selector: 'app-wikipedia-browser',
  templateUrl: './wikipedia-browser.component.html',
  styleUrls: ['./wikipedia-browser.component.css'],
  standalone: true,
  imports: [FormsModule, NgIf, NgFor, DecimalPipe]
})
export class WikipediaBrowserComponent implements OnInit {
  articles: WikipediaArticle[] = [];
  page = 1;
  pageSize = 10;
  totalLoaded = 0;
  totalCount = 0;
  maxPage: number | null = 1;
  loading = false;
  expandedRows: Set<number> = new Set();
  private _activeTab: 'file' | 'alternator' | 'tests' | 'search' = 'search';

  alternatorArticles: any[] = [];
  alternatorStartTitle: string = '';
  alternatorCount: number = 10;
  alternatorLoading: boolean = false;
  alternatorExpandedRows: Set<number> = new Set();
  alternatorNextKey: string | null = null;

  // Test tab state
  testResults: any = null;
  testPartial: string | null = null;
  testRunning: boolean = false;
  testPollInterval: any = null;

  // Search tab state
  searchQuery: string = '';
  searchResults: { title: string; text: string }[] = [];
  searchLoading: boolean = false;
  searchError: string = '';

  // Flag to show/hide the file dump tab
  showFileDumpTab: boolean = false;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.http.get<{ has_wikipedia: boolean }>('/api/has-wikipedia-config').subscribe({
      next: res => {
        this.showFileDumpTab = res.has_wikipedia;
        // If wikipedia is missing and file tab is active, switch to search
        if (!this.showFileDumpTab && this._activeTab === 'file') {
          this._activeTab = 'search';
        }
        if(this.showFileDumpTab) {
          this.loadArticles();
        }
      },
      error: _err => {
        this.showFileDumpTab = false;
        if (this._activeTab === 'file') {
          this._activeTab = 'search';
        }
      }
    });
    this.pollTestResults();
    // Optionally, load alternator articles on init
    // this.loadAlternatorArticles();
  }

  loadArticles() {
    this.loading = true;
    const start = (this.page - 1) * this.pageSize;
    this.http.get<any>(`/api/wikipedia-articles?start=${start}&count=${this.pageSize}`)
      .subscribe(res => {
        this.articles = res.articles;
        this.totalLoaded = this.articles.length;
        this.loading = false;
        if (res.totalCount !== undefined) {
          this.totalCount = res.totalCount;
          this.maxPage = Math.max(1, Math.ceil(this.totalCount / this.pageSize));
        } else {
          this.maxPage = null;
        }
      });
  }

  onAlternatorStartTitleChange() {
    this.loadAlternatorArticles();
  }

  onAlternatorCountChange() {
    this.loadAlternatorArticles();
  }

  loadAlternatorArticles() {
    this.alternatorLoading = true;
    let startTitle = this.alternatorStartTitle;
    let count = this.alternatorCount + 1; // Fetch one extra for navigation
    const params = [
      startTitle ? `start_title=${encodeURIComponent(startTitle)}` : '',
      `count=${count}`
    ].filter(Boolean).join('&');
    this.http.get<any>(`/api/get_articles_page_from?${params}`)
      .subscribe(res => {
        let articles = res.articles || [];
        let hasExtra = articles.length > this.alternatorCount;
        if (hasExtra) {
          this.alternatorNextKey = articles[this.alternatorCount].title;
          articles = articles.slice(0, this.alternatorCount);
        } else {
          this.alternatorNextKey = null;
        }
        this.alternatorStartTitle = articles.length > 0 ? articles[0].title : "";
        this.alternatorArticles = articles;
        this.alternatorLoading = false;
        this.alternatorExpandedRows.clear();
      }, _err => {
        this.alternatorArticles = [];
        this.alternatorLoading = false;
      });
  }

  nextPage() {
    this.page++;
    this.loadArticles();
  }

  prevPage() {
    if (this.page > 1) {
      this.page--;
      this.loadArticles();
    }
  }

  onPageSizeChange(size: number) {
    this.pageSize = size;
    this.page = 1;
    this.loadArticles();
  }

  alternatorNextPage() {
    if (!this.alternatorNextKey) return;
    this.alternatorStartTitle = this.alternatorNextKey;
    this.loadAlternatorArticles();
  }

  toggleRow(idx: number) {
    if (this.expandedRows.has(idx)) {
      this.expandedRows.delete(idx);
    } else {
      this.expandedRows.add(idx);
    }
  }

  isExpanded(idx: number): boolean {
    return this.expandedRows.has(idx);
  }

  toggleAlternatorRow(idx: number) {
    if (this.alternatorExpandedRows.has(idx)) {
      this.alternatorExpandedRows.delete(idx);
    } else {
      this.alternatorExpandedRows.add(idx);
    }
  }

  isAlternatorExpanded(idx: number): boolean {
    return this.alternatorExpandedRows.has(idx);
  }

  encodeURIComponent(title: string): string {
    return encodeURIComponent(title);
  }

  onManualPageChange() {
    if (this.page < 1) this.page = 1;
    // Only limit to maxPage if we know maxPage (i.e., totalCount is defined)
    if (this.totalCount !== 0 && this.maxPage !== null && this.page > this.maxPage) {
      this.page = this.maxPage;
    }
    this.loadArticles();
  }

  addToAlternator(index: number) {
    const article = this.articles.find(a => a.index === index);
    if (!article) return;
    this.http.post('/api/alternator-wikipedia-article', { index }).subscribe({
      next: () => { article.alternator = true; },
      error: () => { /* Optionally handle error */ }
    });
  }

  removeFromAlternator(title: string) {
    // Only send the request once, but update both tables if present
    this.http.delete('/api/alternator-wikipedia-article', { body: { title } }).subscribe({
      next: () => {
        const article = this.articles.find(a => a.title === title);
        if (article) article.alternator = false;
        // Optionally remove from the list or refresh
        this.loadAlternatorArticles();
      },
      error: () => { /* Optionally handle error */ }
    });
  }

  openWikipedia(title: string) {
    window.open('https://en.wikipedia.org/wiki/' + encodeURIComponent(title), '_blank');
  }

  set activeTab(tab: 'file' | 'alternator' | 'tests' | 'search') {
    this._activeTab = tab;
    if (tab === 'alternator') {
      this.loadAlternatorArticles();
    }
    if (tab === 'tests') {
      this.pollTestResults();
    }
    if (tab === 'search') {
      this.searchResults = [];
      this.searchError = '';
      this.searchQuery = '';
    }
  }
  get activeTab() {
    return this._activeTab;
  }

  runTests() {
    this.testRunning = true;
    this.testResults = null;
    this.testPartial = null;
    this.http.post('/api/run-tests', {}, { responseType: 'json' }).subscribe(() => {
      this.pollTestResults();
    });
  }

  pollTestResults() {
    if (this.testPollInterval) {
      clearInterval(this.testPollInterval);
    }
    const poll = () => {
      this.http.get<any>('/api/test-results').subscribe(res => {
        this.testRunning = res.running;
        this.testResults = res.results;
        this.testPartial = res.partial;
        if (this.testRunning) {
          if (!this.testPollInterval) {
            this.testPollInterval = setInterval(poll, 1500);
          }
        } else {
          if (this.testPollInterval) {
            clearInterval(this.testPollInterval);
            this.testPollInterval = null;
          }
        }
      });
    };
    poll();
  }

  searchArticles() {
    if (!this.searchQuery.trim()) {
      this.searchError = 'Please enter a query string.';
      return;
    }
    this.searchLoading = true;
    this.searchError = '';
    this.searchResults = [];
    this.http.get<any>(`/api/query-articles?string_query=${encodeURIComponent(this.searchQuery)}`)
      .subscribe({
        next: res => {
          this.searchResults = res.articles || [];
          this.searchLoading = false;
        },
        error: err => {
          this.searchError = err.error?.error || 'Search failed.';
          this.searchLoading = false;
        }
      });
  }

  getHighlightedText(text: string): string {
    if (!this.searchQuery) return text;
    // Escape regex special characters in searchQuery
    const escaped = this.searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(escaped, 'gi');
    return text.replace(regex, match => `<mark>${match}</mark>`);
  }

  getPreviewWithSearch(text: string, onlyCheck: boolean = false): string {
    if (!this.searchQuery) {
      // Default: first 3 lines
      const lines = text.split('\n');
      if (onlyCheck) return lines.length > 3 ? '...' : '';
      return lines.slice(0, 3).join('\n');
    }
    const lines = text.split('\n');
    // Find the first line containing the search string (case-insensitive)
    const idx = lines.findIndex(line => line.toLowerCase().includes(this.searchQuery.toLowerCase()));
    if (idx === -1) {
      if (onlyCheck) return lines.length > 3 ? '...' : '';
      return lines.slice(0, 3).join('\n');
    }
    // Show up to 3 lines starting from the first match
    const trimmed = idx > 0;
    if (onlyCheck) return (lines.length - idx) > 3 ? '...' : '';
    let preview = lines.slice(idx, idx + 3).join('\n');
    if (trimmed) preview = '[...]\n' + preview;
    return preview;
  }
}
