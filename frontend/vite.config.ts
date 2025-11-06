import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import type { IncomingMessage, ServerResponse, OutgoingHttpHeaders } from "http";

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
        // 개발 환경: Vite HMR 및 개발 도구를 위해 일부 완화
        ? "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob: https: http://localhost:5000 http://localhost:8000; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' http://localhost:5000 http://localhost:8000 ws://localhost:3000 ws://localhost:5173; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; media-src 'self' blob:; worker-src 'self' blob:; manifest-src 'self'"
        // 프로덕션: 보안 강화 (nonce는 서버에서 주입, 여기서는 기본값 사용)
        : "default-src 'self'; script-src 'self' 'nonce-{NONCE}'; style-src 'self' 'nonce-{NONCE}' https://fonts.googleapis.com; style-src-elem 'self' 'nonce-{NONCE}' https://fonts.googleapis.com; img-src 'self' data: blob:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' https://api.privalert.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; media-src 'self' blob:; worker-src 'self'; manifest-src 'self'; upgrade-insecure-requests";
      
      // 관리자 페이지용 - 더 엄격한 CSP (unsafe-inline 완전 제거)
      const adminCSP = "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; style-src-elem 'self' https://fonts.googleapis.com; img-src 'self' data: blob:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; media-src 'self' blob:; worker-src 'none'; manifest-src 'self'; upgrade-insecure-requests";
      
      // 보안 헤더 설정 함수
      const setSecurityHeaders = (req: IncomingMessage, res: ServerResponse) => {
        const url = req.url || '';
        
        // 모든 응답에 기본 보안 헤더 설정 (정적 리소스 포함)
        res.setHeader('X-Content-Type-Options', 'nosniff');
        res.setHeader('X-Frame-Options', 'DENY'); // 모든 프레임 차단
        res.setHeader('X-XSS-Protection', '1; mode=block');
        res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
        res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=()');
        
        // CSP는 HTML 페이지만 설정 (정적 리소스에는 불필요하지만 설정해도 무방)
        // 경로에 따라 적절한 CSP 선택
        let csp: string;
        if (url === '/sitemap.xml' || url.startsWith('/sitemap.xml?')) {
          csp = sitemapCSP;
        } else if (url === '/robots.txt' || url.startsWith('/robots.txt?')) {
          csp = robotsCSP;
        } else if (url.startsWith('/admin')) {
          csp = adminCSP;
        } else if (url.match(/\.(html|htm)$/i) || url === '/' || url === '') {
          // HTML 페이지만 CSP 설정
          csp = htmlCSP;
        } else {
          // 정적 리소스 (JS, CSS, 이미지 등)에도 기본 CSP 설정
          // 하지만 더 관대한 정책 사용
          csp = "default-src 'self'; frame-ancestors 'none'";
        }
        
        // 클릭재킹 방지 헤더 (CSP와 X-Frame-Options 둘 다 설정)
        // CSP의 frame-ancestors와 X-Frame-Options 모두 설정하여 최대 호환성 보장
        res.setHeader('Content-Security-Policy', csp);
      };
      
      // 미들웨어를 가장 먼저 실행되도록 설정 (다른 미들웨어보다 우선)
      // 모든 요청에 대해 보안 헤더 강제 적용
      // Vite의 기본 미들웨어보다 먼저 실행되도록 unshift 사용
      if (Array.isArray(server.middlewares.stack)) {
        server.middlewares.stack.unshift({
          route: '',
          handle: (req: IncomingMessage, res: ServerResponse, next: () => void) => {
            // 모든 요청에 대해 보안 헤더 설정
            setSecurityHeaders(req, res);
            next();
          }
        });
      } else {
        // fallback: use 메서드 사용
        server.middlewares.use((req: IncomingMessage, res: ServerResponse, next: () => void) => {
          setSecurityHeaders(req, res);
          next();
        });
      }
      
      // 응답이 전송되기 전에 헤더가 설정되었는지 다시 확인 (이중 보장)
      server.middlewares.use((req, res, next) => {
        const originalEnd = res.end;
        const originalWriteHead = res.writeHead;
        
        // writeHead를 가로채서 헤더 확인
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        res.writeHead = function(statusCode?: any, statusMessage?: any, headers?: any): any {
          let actualHeaders: OutgoingHttpHeaders;
          let actualStatusMessage: string | undefined;
          
          // writeHead 오버로드 처리: (statusCode, headers) 또는 (statusCode, statusMessage, headers)
          if (headers === undefined && typeof statusMessage !== 'string' && typeof statusMessage !== 'number') {
            // 2개 인자: (statusCode, headers)
            actualHeaders = statusMessage as OutgoingHttpHeaders;
            actualStatusMessage = undefined;
          } else {
            // 3개 인자: (statusCode, statusMessage, headers)
            actualHeaders = headers as OutgoingHttpHeaders;
            actualStatusMessage = statusMessage as string | undefined;
          }
          
          // 필수 보안 헤더 강제 설정
          if (actualHeaders) {
            actualHeaders['X-Content-Type-Options'] = 'nosniff';
            actualHeaders['X-Frame-Options'] = 'DENY';
          } else {
            actualHeaders = {
              'X-Content-Type-Options': 'nosniff',
              'X-Frame-Options': 'DENY',
            };
          }
          
          // CSP가 없으면 기본 CSP 추가
          const cspValue = actualHeaders['Content-Security-Policy'];
          if (!cspValue || (typeof cspValue === 'string' && cspValue.length === 0)) {
            const url = req.url || '';
            if (url === '/sitemap.xml' || url.startsWith('/sitemap.xml?')) {
              actualHeaders['Content-Security-Policy'] = sitemapCSP;
            } else if (url === '/robots.txt' || url.startsWith('/robots.txt?')) {
              actualHeaders['Content-Security-Policy'] = robotsCSP;
            } else if (url.startsWith('/admin')) {
              actualHeaders['Content-Security-Policy'] = adminCSP;
            } else {
              actualHeaders['Content-Security-Policy'] = htmlCSP;
            }
          }
          
          // frame-ancestors가 없으면 추가
          const currentCsp = actualHeaders['Content-Security-Policy'];
          if (currentCsp && typeof currentCsp === 'string' && !currentCsp.includes('frame-ancestors')) {
            actualHeaders['Content-Security-Policy'] = currentCsp + '; frame-ancestors \'none\'';
          }
          
          // writeHead는 statusMessage가 있으면 3개 인자, 없으면 2개 인자
          // TypeScript 타입 호환을 위해 타입 단언 사용
          if (actualStatusMessage !== undefined) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalWriteHead as any).call(this, statusCode as number, actualStatusMessage, actualHeaders);
          } else {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalWriteHead as any).call(this, statusCode as number, actualHeaders);
          }
        };
        
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        res.end = function(chunk?: any, encoding?: any, cb?: any): any {
          // 응답이 전송되기 전에 헤더 확인 및 설정 (강제)
          if (!res.headersSent) {
            // 보안 헤더 강제 설정
            setSecurityHeaders(req, res);
          } else {
            // 헤더가 이미 전송되었더라도, 필수 헤더는 반드시 설정되어야 함
            // 하지만 headersSent가 true이면 setHeader가 작동하지 않으므로
            // writeHead를 통해 강제로 헤더 추가 시도
            try {
              const existingHeaders: OutgoingHttpHeaders = {};
              res.getHeaderNames().forEach(name => {
                const value = res.getHeader(name);
                if (value) {
                  existingHeaders[name] = value;
                }
              });
              
              // 필수 보안 헤더 확인 및 추가
              if (!existingHeaders['X-Content-Type-Options']) {
                existingHeaders['X-Content-Type-Options'] = 'nosniff';
              }
              if (!existingHeaders['X-Frame-Options']) {
                existingHeaders['X-Frame-Options'] = 'DENY';
              }
              if (!existingHeaders['Content-Security-Policy']) {
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
                existingHeaders['Content-Security-Policy'] = csp;
              }
            } catch (e) {
              // 헤더가 이미 전송된 경우 무시
            }
          }
          
          // 필수 보안 헤더 이중 보장 (headersSent가 false인 경우에만)
          if (!res.headersSent) {
            if (!res.getHeader('X-Content-Type-Options')) {
              res.setHeader('X-Content-Type-Options', 'nosniff');
            }
            if (!res.getHeader('X-Frame-Options')) {
              res.setHeader('X-Frame-Options', 'DENY');
            }
            
            // CSP 확인 및 설정
            let csp = res.getHeader('Content-Security-Policy');
            if (!csp) {
              const url = req.url || '';
              if (url === '/sitemap.xml' || url.startsWith('/sitemap.xml?')) {
                csp = sitemapCSP;
              } else if (url === '/robots.txt' || url.startsWith('/robots.txt?')) {
                csp = robotsCSP;
              } else if (url.startsWith('/admin')) {
                csp = adminCSP;
              } else {
                csp = htmlCSP;
              }
              res.setHeader('Content-Security-Policy', csp);
            } else if (typeof csp === 'string' && !csp.includes('frame-ancestors')) {
              res.setHeader('Content-Security-Policy', csp + '; frame-ancestors \'none\'');
            }
          }
          
          // res.end 오버로드 처리: (cb) 또는 (chunk, cb) 또는 (chunk, encoding, cb)
          if (chunk === undefined && encoding === undefined && cb === undefined) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalEnd as any).call(this);
          } else if (encoding === undefined && typeof cb === 'function') {
            // (chunk, cb) 또는 (cb)
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalEnd as any).call(this, chunk, cb);
          } else if (encoding !== undefined && typeof encoding !== 'string') {
            // (chunk, cb) - encoding이 실제로는 cb
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalEnd as any).call(this, chunk, encoding);
          } else {
            // (chunk, encoding, cb)
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalEnd as any).call(this, chunk, encoding, cb);
          }
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
      // 보안: blob: URL 허용 (로컬 파일 미리보기용), worker-src는 'self'만 허용
      const htmlCSP = "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; style-src-elem 'self' https://fonts.googleapis.com; img-src 'self' data: blob:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; media-src 'self' blob:; worker-src 'self'; manifest-src 'self'";
      
      // 관리자 페이지용
      const adminCSP = "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; style-src-elem 'self' https://fonts.googleapis.com; img-src 'self' data: blob:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; media-src 'self' blob:; worker-src 'none'; manifest-src 'self'; upgrade-insecure-requests";
      
      // 보안 헤더 설정 함수
      const setSecurityHeaders = (req: IncomingMessage, res: ServerResponse) => {
        const url = req.url || '';
        
        // 모든 응답에 기본 보안 헤더 설정 (정적 리소스 포함)
        res.setHeader('X-Content-Type-Options', 'nosniff');
        res.setHeader('X-Frame-Options', 'DENY'); // 모든 프레임 차단
        res.setHeader('X-XSS-Protection', '1; mode=block');
        res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
        res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=()');
        
        // CSP는 HTML 페이지만 설정 (정적 리소스에는 불필요하지만 설정해도 무방)
        let csp: string;
        if (url === '/sitemap.xml' || url.startsWith('/sitemap.xml?')) {
          csp = sitemapCSP;
        } else if (url === '/robots.txt' || url.startsWith('/robots.txt?')) {
          csp = robotsCSP;
        } else if (url.startsWith('/admin')) {
          csp = adminCSP;
        } else if (url.match(/\.(html|htm)$/i) || url === '/' || url === '') {
          // HTML 페이지만 CSP 설정
          csp = htmlCSP;
        } else {
          // 정적 리소스 (JS, CSS, 이미지 등)에도 기본 CSP 설정
          // 하지만 더 관대한 정책 사용
          csp = "default-src 'self'; frame-ancestors 'none'";
        }
        
        // 클릭재킹 방지 헤더 (CSP와 X-Frame-Options 둘 다 설정)
        res.setHeader('Content-Security-Policy', csp);
      };
      
      // 미들웨어를 가장 먼저 실행되도록 설정
      // Vite의 기본 미들웨어보다 먼저 실행되도록 unshift 사용
      if (Array.isArray(server.middlewares.stack)) {
        server.middlewares.stack.unshift({
          route: '',
          handle: (req: IncomingMessage, res: ServerResponse, next: () => void) => {
            // 모든 요청에 대해 보안 헤더 설정
            setSecurityHeaders(req, res);
            next();
          }
        });
      } else {
        // fallback: use 메서드 사용
        server.middlewares.use((req: IncomingMessage, res: ServerResponse, next: () => void) => {
          setSecurityHeaders(req, res);
          next();
        });
      }
      
      // 응답 전송 전 헤더 재확인 (이중 보장)
      server.middlewares.use((req, res, next) => {
        const originalEnd = res.end;
        const originalWriteHead = res.writeHead;
        
        // writeHead를 가로채서 헤더 확인
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        res.writeHead = function(statusCode?: any, statusMessage?: any, headers?: any): any {
          let actualHeaders: OutgoingHttpHeaders;
          let actualStatusMessage: string | undefined;
          
          // writeHead 오버로드 처리: (statusCode, headers) 또는 (statusCode, statusMessage, headers)
          if (headers === undefined && typeof statusMessage !== 'string' && typeof statusMessage !== 'number') {
            // 2개 인자: (statusCode, headers)
            actualHeaders = statusMessage as OutgoingHttpHeaders;
            actualStatusMessage = undefined;
          } else {
            // 3개 인자: (statusCode, statusMessage, headers)
            actualHeaders = headers as OutgoingHttpHeaders;
            actualStatusMessage = statusMessage as string | undefined;
          }
          
          // 필수 보안 헤더 강제 설정
          if (actualHeaders) {
            actualHeaders['X-Content-Type-Options'] = 'nosniff';
            actualHeaders['X-Frame-Options'] = 'DENY';
          } else {
            actualHeaders = {
              'X-Content-Type-Options': 'nosniff',
              'X-Frame-Options': 'DENY',
            };
          }
          
          // CSP가 없으면 기본 CSP 추가
          const cspValue = actualHeaders['Content-Security-Policy'];
          if (!cspValue || (typeof cspValue === 'string' && cspValue.length === 0)) {
            const url = req.url || '';
            if (url === '/sitemap.xml' || url.startsWith('/sitemap.xml?')) {
              actualHeaders['Content-Security-Policy'] = sitemapCSP;
            } else if (url === '/robots.txt' || url.startsWith('/robots.txt?')) {
              actualHeaders['Content-Security-Policy'] = robotsCSP;
            } else if (url.startsWith('/admin')) {
              actualHeaders['Content-Security-Policy'] = adminCSP;
            } else {
              actualHeaders['Content-Security-Policy'] = htmlCSP;
            }
          }
          
          // frame-ancestors가 없으면 추가
          const currentCsp = actualHeaders['Content-Security-Policy'];
          if (currentCsp && typeof currentCsp === 'string' && !currentCsp.includes('frame-ancestors')) {
            actualHeaders['Content-Security-Policy'] = currentCsp + '; frame-ancestors \'none\'';
          }
          
          // writeHead는 statusMessage가 있으면 3개 인자, 없으면 2개 인자
          // TypeScript 타입 호환을 위해 타입 단언 사용
          if (actualStatusMessage !== undefined) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalWriteHead as any).call(this, statusCode as number, actualStatusMessage, actualHeaders);
          } else {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalWriteHead as any).call(this, statusCode as number, actualHeaders);
          }
        };
        
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        res.end = function(chunk?: any, encoding?: any, cb?: any): any {
          // 응답이 전송되기 전에 헤더 확인 및 설정 (강제)
          if (!res.headersSent) {
            // 보안 헤더 강제 설정
            setSecurityHeaders(req, res);
          }
          
          // 필수 보안 헤더 이중 보장 (headersSent가 false인 경우에만)
          if (!res.headersSent) {
            if (!res.getHeader('X-Content-Type-Options')) {
              res.setHeader('X-Content-Type-Options', 'nosniff');
            }
            if (!res.getHeader('X-Frame-Options')) {
              res.setHeader('X-Frame-Options', 'DENY');
            }
            
            // CSP 확인 및 설정
            let csp = res.getHeader('Content-Security-Policy');
            if (!csp) {
              const url = req.url || '';
              if (url === '/sitemap.xml' || url.startsWith('/sitemap.xml?')) {
                csp = sitemapCSP;
              } else if (url === '/robots.txt' || url.startsWith('/robots.txt?')) {
                csp = robotsCSP;
              } else if (url.startsWith('/admin')) {
                csp = adminCSP;
              } else {
                csp = htmlCSP;
              }
              res.setHeader('Content-Security-Policy', csp);
            } else if (typeof csp === 'string' && !csp.includes('frame-ancestors')) {
              res.setHeader('Content-Security-Policy', csp + '; frame-ancestors \'none\'');
            }
          }
          
          // res.end 오버로드 처리: (cb) 또는 (chunk, cb) 또는 (chunk, encoding, cb)
          if (chunk === undefined && encoding === undefined && cb === undefined) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalEnd as any).call(this);
          } else if (encoding === undefined && typeof cb === 'function') {
            // (chunk, cb) 또는 (cb)
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalEnd as any).call(this, chunk, cb);
          } else if (encoding !== undefined && typeof encoding !== 'string') {
            // (chunk, cb) - encoding이 실제로는 cb
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalEnd as any).call(this, chunk, encoding);
          } else {
            // (chunk, encoding, cb)
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (originalEnd as any).call(this, chunk, encoding, cb);
          }
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
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
