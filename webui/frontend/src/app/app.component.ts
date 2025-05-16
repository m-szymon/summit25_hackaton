import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
  standalone: true,
  imports: [NgIf]
})
export class AppComponent implements OnInit {
  deadline: Date | null = null;
  deadlineString: string = '';
  timeLeft: string = '';
  private timer: any;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.http.get<{ deadline: string }>('/api/deadline').subscribe(res => {
      this.deadline = new Date(res.deadline);
      this.deadlineString = this.formatDeadline(this.deadline);
      this.updateTimeLeft();
      this.timer = setInterval(() => this.updateTimeLeft(), 1000);
    });
  }

  updateTimeLeft() {
    if (!this.deadline) return;
    const now = new Date();
    const diff = this.deadline.getTime() - now.getTime();
    if (diff <= 0) {
      this.timeLeft = '0d 0h 0m 0s';
      clearInterval(this.timer);
      return;
    }
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
    const minutes = Math.floor((diff / (1000 * 60)) % 60);
    const seconds = Math.floor((diff / 1000) % 60);
    this.timeLeft = `${days}d ${hours}h ${minutes}m ${seconds}s`;
  }

  formatDeadline(date: Date): string {
    // Format as YYYY-MM-DD HH:mm:ss (local browser time)
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())} ` +
           `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  }

  isAfterDeadline(): boolean {
    if (!this.deadline) return false;
    return new Date() > this.deadline;
  }
}
