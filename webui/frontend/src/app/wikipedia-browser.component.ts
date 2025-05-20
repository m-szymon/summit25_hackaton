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
  private _activeTab: 'file' | 'alternator' | 'tests' = 'file';

  alternatorArticles: any[] = [];
  alternatorStartTitle: string = '';
  alternatorCount: number = 10;
  alternatorLoading: boolean = false;
  alternatorExpandedRows: Set<number> = new Set();
  alternatorNextKey: string | null = null;
  alternatorPrevKey: string | null = null;

  // Test tab state
  testResults: any = null;
  testPartial: string | null = null;
  testRunning: boolean = false;
  testPollInterval: any = null;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadArticles();
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

  loadAlternatorArticles(direction: 'forward' | 'backward' = 'forward') {
    this.alternatorLoading = true;
    let startTitle = this.alternatorStartTitle;
    let count = this.alternatorCount + 1; // Fetch one extra for navigation
    let forward = true;
    if (direction === 'backward') {
      forward = false;
    }
    const params = [
      startTitle ? `start_title=${encodeURIComponent(startTitle)}` : '',
      `count=${count}`,
      `forward=${forward}`
    ].filter(Boolean).join('&');
    this.http.get<any>(`/api/get_articles_page_from?${params}`)
      .subscribe(res => {
        let articles = res.articles || [];
        let hasExtra = articles.length > this.alternatorCount;
        if (direction === 'backward') {
          // Backward: reverse to display in original order
          articles = articles.reverse();
        }
        if (hasExtra) {
          this.alternatorNextKey = articles[this.alternatorCount].title;
          articles = articles.slice(0, this.alternatorCount);
        } else {
          this.alternatorNextKey = null;
        }
        this.alternatorStartTitle = articles.length > 0 ? articles[0].title : "";
        this.alternatorPrevKey = this.alternatorStartTitle;
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
    this.loadAlternatorArticles('forward');
  }

  alternatorPrevPage() {
    if (!this.alternatorPrevKey) return;
    this.alternatorStartTitle = this.alternatorPrevKey;
    this.loadAlternatorArticles('backward');
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

  set activeTab(tab: 'file' | 'alternator' | 'tests') {
    this._activeTab = tab;
    if (tab === 'alternator') {
      this.loadAlternatorArticles();
    }
    if (tab === 'tests') {
      this.pollTestResults();
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
}
