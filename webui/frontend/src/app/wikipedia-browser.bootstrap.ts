import { bootstrapApplication } from '@angular/platform-browser';
import { WikipediaBrowserComponent } from './wikipedia-browser.component';
import { provideHttpClient } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';
import { importProvidersFrom } from '@angular/core';
import { FormsModule } from '@angular/forms';

export const wikipediaBrowserConfig = {
  providers: [
    provideHttpClient(),
    provideAnimations(),
    importProvidersFrom(FormsModule)
  ]
};

export function bootstrapWikipediaBrowserComponent(container: HTMLElement) {
  bootstrapApplication(WikipediaBrowserComponent, wikipediaBrowserConfig)
    .then(appRef => {
      container.appendChild(document.createElement('app-wikipedia-browser'));
    })
    .catch(err => console.error(err));
}
