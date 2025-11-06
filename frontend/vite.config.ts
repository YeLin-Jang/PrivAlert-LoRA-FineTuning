import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// 보안 헤더 미들웨어 플러그인
function securityHeadersPlugin(): Plugin {
  return {
    name: "security-headers",
    configureServer(server) {
      // sitemap.xml 전용 - 가장 엄격한 CSP (정적 XML 리소스)
      const sitemapCSP = "default-src 'none'; object-src 'none'; script-src 'none'; style-src 'none'; connect-src 'none'; img-src 'none'; frame-ancestors 'none'";
      
      // robots.txt 전용 - 텍스트 파일 (스크립트 불필요)
      const robotsCSP = "default-src 'none'; script-src 'none'; style-src 'none'; connect-src 'none'; frame-ancestors 'none'";
      
      // HTML 페이지용 - 개발 환경에서는 Vite HMR을 위해 unsafe-inline 허용
      // 보안: 프로덕션에서는 unsafe-inline 제거, 개발 환경에서는 Vite 작동을 위해 필요
      const isDev = process.env.NODE_ENV !== 'production';
      const htmlCSP = isDev
        ? "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob: https:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' http://localhost:5000 http://localhost:8000 ws://localhost:3000 ws://localhost:5173; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; media-src 'self' blob:; worker-src 'none'; manifest-src 'self'"
        : "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; style-src-elem 'self' https://fonts.googleapis.com; img-src 'self' data: blob:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' http://localhost:5000 http://localhost:8000 ws://localhost:3000 ws://localhost:5173; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; media-src 'self' blob:; worker-src 'none'; manifest-src 'self'";
      
      // 관리자 페이지용 - 더 엄격한 CSP (unsafe-inline 완전 제거)
      const adminCSP = "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; style-src-elem 'self' https://fonts.googleapis.com; img-src 'self' data: blob:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; media-src 'self' blob:; worker-src 'none'; manifest-src 'self'; upgrade-insecure-requests";
      
      // 보안 헤더 설정 함수
      const setSecurityHeaders = (req: any, res: any) => {
        const url = req.url || '';
        
        // 경로에 따라 적절한 CSP 선택
        let csp: string;
        if (url === '/sitemap.xml' || url.startsWith('/sitemap.xml?')) {
          csp = sitemapCSP;
        } else if (url === '/robots.txt' || url.startsWith('/robots.txt?')) {
          csp = robotsCSP;
        } else if (url.startsWith('/admin')) {
          csp = adminCSP;
        } else {
          // HTML 페이지 (/, /index.html 등)
          csp = htmlCSP;
        }
        
        // 클릭재킹 방지 헤더 (CSP와 X-Frame-Options 둘 다 설정)
        // CSP의 frame-ancestors와 X-Frame-Options 모두 설정하여 최대 호환성 보장
        res.setHeader('Content-Security-Policy', csp);
        res.setHeader('X-Frame-Options', 'DENY'); // 모든 프레임 차단
        
        // 기타 보안 헤더
        res.setHeader('X-Content-Type-Options', 'nosniff');
        res.setHeader('X-XSS-Protection', '1; mode=block');
        res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
        res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=()');
      };
      
      // 미들웨어를 가장 먼저 실행되도록 설정 (다른 미들웨어보다 우선)
      // 모든 요청에 대해 보안 헤더 강제 적용
      server.middlewares.use((req, res, next) => {
        // 헤더가 이미 설정되었는지 확인하고, 없으면 설정
        if (!res.headersSent) {
          setSecurityHeaders(req, res);
        }
        next();
      });
      
      // 응답이 전송되기 전에 헤더가 설정되었는지 다시 확인
      server.middlewares.use((req, res, next) => {
        const originalEnd = res.end;
        const originalWriteHead = res.writeHead;
        
        // writeHead를 가로채서 헤더 확인
        res.writeHead = function(statusCode?: number, statusMessage?: any, headers?: any) {
          if (!headers) {
            headers = statusMessage;
            statusMessage = undefined;
          }
          
          // 필수 보안 헤더 강제 설정
          if (headers) {
            headers['X-Content-Type-Options'] = 'nosniff';
            headers['X-Frame-Options'] = 'DENY';
          } else {
            headers = {
              'X-Content-Type-Options': 'nosniff',
              'X-Frame-Options': 'DENY',
            };
          }
          
          // CSP가 없으면 기본 CSP 추가
          if (!headers['Content-Security-Policy']) {
            const url = req.url || '';
            if (url === '/sitemap.xml' || url.startsWith('/sitemap.xml?')) {
              headers['Content-Security-Policy'] = sitemapCSP;
            } else if (url === '/robots.txt' || url.startsWith('/robots.txt?')) {
              headers['Content-Security-Policy'] = robotsCSP;
            } else if (url.startsWith('/admin')) {
              headers['Content-Security-Policy'] = adminCSP;
            } else {
              headers['Content-Security-Policy'] = htmlCSP;
            }
          }
          
          // frame-ancestors가 없으면 추가
          if (headers['Content-Security-Policy'] && !headers['Content-Security-Policy'].includes('frame-ancestors')) {
            headers['Content-Security-Policy'] += '; frame-ancestors \'none\'';
          }
          
          // writeHead는 statusMessage가 있으면 3개 인자, 없으면 2개 인자
          // TypeScript 타입 호환을 위해 타입 단언 사용
          if (statusMessage !== undefined) {
            return (originalWriteHead as any).call(this, statusCode as number, statusMessage, headers);
          } else {
            return (originalWriteHead as any).call(this, statusCode as number, headers);
          }
        };
        
        res.end = function(chunk?: any, encoding?: any, cb?: any) {
          // 응답이 전송되기 전에 헤더 확인 및 설정
          if (!res.headersSent) {
            setSecurityHeaders(req, res);
          }
          
          // 필수 보안 헤더 이중 보장
          if (!res.getHeader('X-Content-Type-Options')) {
            res.setHeader('X-Content-Type-Options', 'nosniff');
          }
          if (!res.getHeader('X-Frame-Options')) {
            res.setHeader('X-Frame-Options', 'DENY');
          }
          
          // CSP의 frame-ancestors가 없으면 추가
          const csp = res.getHeader('Content-Security-Policy');
          if (csp && typeof csp === 'string' && !csp.includes('frame-ancestors')) {
            res.setHeader('Content-Security-Policy', csp + '; frame-ancestors \'none\'');
          }
          
          return originalEnd.call(this, chunk, encoding, cb);
        };
        next();
      });
    },
    configurePreviewServer(server) {
      // 프로덕션 프리뷰 서버용 CSP
      // sitemap.xml 전용 - 가장 엄격한 CSP
      const sitemapCSP = "default-src 'none'; object-src 'none'; script-src 'none'; style-src 'none'; connect-src 'none'; img-src 'none'; frame-ancestors 'none'";
      
      // robots.txt 전용
      const robotsCSP = "default-src 'none'; script-src 'none'; style-src 'none'; connect-src 'none'; frame-ancestors 'none'";
      
      // HTML 페이지용 - unsafe-inline, unsafe-eval 완전 제거
      // 보안: blob: URL 허용 (로컬 파일 미리보기용)
      const htmlCSP = "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; style-src-elem 'self' https://fonts.googleapis.com; img-src 'self' data: blob:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; media-src 'self' blob:; worker-src 'none'; manifest-src 'self'";
      
      // 관리자 페이지용
      const adminCSP = "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; style-src-elem 'self' https://fonts.googleapis.com; img-src 'self' data: blob:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; media-src 'self' blob:; worker-src 'none'; manifest-src 'self'; upgrade-insecure-requests";
      
      // 보안 헤더 설정 함수
      const setSecurityHeaders = (req: any, res: any) => {
        const url = req.url || '';
        
        let csp: string;
        if (url === '/sitemap.xml' || url.startsWith('/sitemap.xml?')) {
          csp = sitemapCSP;
        } else if (url === '/robots.txt' || url.startsWith('/robots.txt?')) {
          csp = robotsCSP;
        } else if (url.startsWith('/admin')) {
          csp = adminCSP;
        } else {
          csp = htmlCSP;
        }
        
        // 클릭재킹 방지 헤더 (CSP와 X-Frame-Options 둘 다 설정)
        res.setHeader('Content-Security-Policy', csp);
        res.setHeader('X-Frame-Options', 'DENY'); // 모든 프레임 차단
        
        // 기타 보안 헤더
        res.setHeader('X-Content-Type-Options', 'nosniff');
        res.setHeader('X-XSS-Protection', '1; mode=block');
        res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
        res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=()');
      };
      
      // 미들웨어를 가장 먼저 실행되도록 설정
      server.middlewares.use((req, res, next) => {
        if (!res.headersSent) {
          setSecurityHeaders(req, res);
        }
        next();
      });
      
      // 응답 전송 전 헤더 재확인
      server.middlewares.use((req, res, next) => {
        const originalEnd = res.end;
        const originalWriteHead = res.writeHead;
        
        // writeHead를 가로채서 헤더 확인
        res.writeHead = function(statusCode?: number, statusMessage?: any, headers?: any) {
          if (!headers) {
            headers = statusMessage;
            statusMessage = undefined;
          }
          
          // 필수 보안 헤더 강제 설정
          if (headers) {
            headers['X-Content-Type-Options'] = 'nosniff';
            headers['X-Frame-Options'] = 'DENY';
          } else {
            headers = {
              'X-Content-Type-Options': 'nosniff',
              'X-Frame-Options': 'DENY',
            };
          }
          
          // CSP가 없으면 기본 CSP 추가
          if (!headers['Content-Security-Policy']) {
            const url = req.url || '';
            if (url === '/sitemap.xml' || url.startsWith('/sitemap.xml?')) {
              headers['Content-Security-Policy'] = sitemapCSP;
            } else if (url === '/robots.txt' || url.startsWith('/robots.txt?')) {
              headers['Content-Security-Policy'] = robotsCSP;
            } else if (url.startsWith('/admin')) {
              headers['Content-Security-Policy'] = adminCSP;
            } else {
              headers['Content-Security-Policy'] = htmlCSP;
            }
          }
          
          // frame-ancestors가 없으면 추가
          if (headers['Content-Security-Policy'] && !headers['Content-Security-Policy'].includes('frame-ancestors')) {
            headers['Content-Security-Policy'] += '; frame-ancestors \'none\'';
          }
          
          // writeHead는 statusMessage가 있으면 3개 인자, 없으면 2개 인자
          // TypeScript 타입 호환을 위해 타입 단언 사용
          if (statusMessage !== undefined) {
            return (originalWriteHead as any).call(this, statusCode as number, statusMessage, headers);
          } else {
            return (originalWriteHead as any).call(this, statusCode as number, headers);
          }
        };
        
        res.end = function(chunk?: any, encoding?: any, cb?: any) {
          if (!res.headersSent) {
            setSecurityHeaders(req, res);
          }
          
          // 필수 보안 헤더 이중 보장
          if (!res.getHeader('X-Content-Type-Options')) {
            res.setHeader('X-Content-Type-Options', 'nosniff');
          }
          if (!res.getHeader('X-Frame-Options')) {
            res.setHeader('X-Frame-Options', 'DENY');
          }
          
          // CSP의 frame-ancestors가 없으면 추가
          const csp = res.getHeader('Content-Security-Policy');
          if (csp && typeof csp === 'string' && !csp.includes('frame-ancestors')) {
            res.setHeader('Content-Security-Policy', csp + '; frame-ancestors \'none\'');
          }
          
          return originalEnd.call(this, chunk, encoding, cb);
        };
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [
    // React 플러그인: 프로덕션에서 개발 모드 비활성화
    react({
      // 보안: 프로덕션 빌드에서 개발 모드 경고 제거
      jsxRuntime: 'automatic',
    }),
    securityHeadersPlugin(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    strictPort: true, // 포트가 사용 중이면 에러 발생 (자동으로 다른 포트 사용 안 함)
  },
  preview: {
    port: 3000,
  },
  build: {
    // 프로덕션 빌드 최적화 및 보안 강화
    minify: 'terser',
    terserOptions: {
      // TerserOptions 타입 호환: compress 옵션을 최상위로 이동
      compress: {
        // 보안: 프로덕션 빌드에서 모든 주석 및 디버그 코드 제거
        drop_console: true, // 모든 console.* 제거
        drop_debugger: true, // debugger 제거
        pure_funcs: [
          'console.log',
          'console.info',
          'console.debug',
          'console.trace',
          'console.warn',
          'console.error',
          'console.group',
          'console.groupEnd',
          'console.table',
          'console.time',
          'console.timeEnd',
        ],
        // 디버그 관련 키워드 제거
        passes: 3, // 여러 번 압축하여 더 철저한 최적화
      },
      format: {
        // 보안: 주석 완전 제거
        comments: false,
        // 보안: 디버그 정보 제거
        beautify: false,
        // 보안: 소스맵 URL 제거
        ascii_only: true,
      },
      // 보안: 주석 제거 옵션 (format.comments와 중복되지만 명시적으로 설정)
      keep_classnames: false,
      keep_fnames: false,
    } as any, // TerserOptions 타입 호환성 문제 해결
    // 소스맵 생성 비활성화 (보안: 소스 코드 노출 방지)
    sourcemap: false,
    // 청크 크기 경고 비활성화 (프로덕션 빌드 최적화)
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // 보안: 파일명 해시로 추측 방지
        entryFileNames: 'assets/[hash].js',
        chunkFileNames: 'assets/[hash].js',
        assetFileNames: 'assets/[hash].[ext]',
        // 주석 제거
        compact: true,
        // 보안: 라이선스 파일 제거
        banner: undefined,
        footer: undefined,
      },
      // 보안: 외부 모듈의 주석 제거
      external: [],
    },
    // CSS 최적화
    cssCodeSplit: true,
    cssMinify: true,
  },
  // 환경 변수 설정 (빌드 시에만 적용, 개발 모드에서는 Vite가 자동으로 처리)
  // define 옵션은 빌드 시에만 필요한 경우에만 사용
  // 개발 모드에서는 Vite가 자동으로 import.meta.env.DEV를 true로 설정
});
